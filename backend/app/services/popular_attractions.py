"""热门景点推荐：从高德 POI 中筛出不在当前行程里的景点。

只做“发现更多”用途：返回名称、地址、坐标、类别、评分和实拍图；
景点深度介绍仍由 ``attraction_guide`` 的现有模板生成，避免两套内容结构。
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, Iterable, List, Optional

import httpx

from ..config import get_settings

_AMAP_PLACE_TEXT = "https://restapi.amap.com/v3/place/text"
_CACHE_TTL_SECONDS = 10 * 60
_CACHE: Dict[str, tuple[float, List[Dict[str, Any]]]] = {}

_ATTRACTION_TYPE_WORDS = (
    "风景名胜", "公园", "博物馆", "纪念馆", "展览馆", "美术馆", "寺", "庙",
    "塔", "楼", "宫", "府", "园", "山", "湖", "街", "古镇", "遗址", "城墙",
    "陵", "祠", "故居", "广场", "景区",
)
_EXCLUDE_TYPE_WORDS = (
    "酒店", "宾馆", "民宿", "餐厅", "饭店", "小吃", "购物", "商场", "车站",
    "机场", "地铁", "公交", "停车场", "加油站", "医院", "学校",
)


def _normalize(text: Any) -> str:
    return re.sub(r"[\s·•,，、/|（）()【】\[\]《》“”\"']+", "", str(text or "").lower())


def _name_key(text: Any) -> str:
    """用于去重/排除的景点名归一：忽略“景区/风景区/公园”等通用后缀。"""
    normalized = _normalize(text)
    for suffix in ("风景区", "景区", "公园", "游览区"):
        if normalized.endswith(suffix) and len(normalized) > len(suffix) + 1:
            return normalized[: -len(suffix)]
    return normalized


def _text(value: Any) -> str:
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value or "").strip()


def _loads(value: Any) -> list:
    if isinstance(value, list):
        return value
    return []


def _parse_location(value: Any) -> Optional[Dict[str, float]]:
    text = _text(value)
    if "," not in text:
        return None
    try:
        lng_text, lat_text = text.split(",", 1)
        lng, lat = float(lng_text), float(lat_text)
    except (TypeError, ValueError):
        return None
    if not (-180 <= lng <= 180 and -90 <= lat <= 90):
        return None
    return {"longitude": lng, "latitude": lat}


def _parse_rating(value: Any) -> Optional[float]:
    text = _text(value)
    if not text:
        return None
    try:
        rating = float(text)
    except ValueError:
        return None
    return rating if 0 < rating <= 5 else None


def _parse_ticket_price(value: Any) -> Optional[int]:
    text = _text(value)
    if not text:
        return None
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        price = float(match.group(0))
    except ValueError:
        return None
    return int(round(price)) if price > 0 else None


def _category(type_text: str) -> str:
    parts = [part for part in str(type_text or "").split(";") if part]
    return parts[-1] if parts else "景点"


def _is_attraction(poi: Dict[str, Any]) -> bool:
    type_text = _text(poi.get("type"))
    name = _text(poi.get("name"))
    haystack = f"{type_text} {name}"
    if any(word in haystack for word in _EXCLUDE_TYPE_WORDS):
        return False
    return any(word in haystack for word in _ATTRACTION_TYPE_WORDS)


def _visit_duration(category: str) -> int:
    if "博物馆" in category or "纪念馆" in category or "展览" in category:
        return 150
    if "公园" in category or "湖" in category or "山" in category:
        return 120
    if "寺" in category or "庙" in category or "塔" in category:
        return 60
    return 90


def _description(name: str, category: str, address: str, rating: Optional[float]) -> str:
    base = f"{name}是当地热门景点，类型为{category}。"
    if address:
        base += f"地址位于{address}。"
    if rating:
        base += f"高德综合评分约 {rating:g} 分。"
    return base


def _photos(poi: Dict[str, Any]) -> List[str]:
    photos = []
    for photo in _loads(poi.get("photos")):
        if isinstance(photo, dict):
            url = _text(photo.get("url"))
        else:
            url = _text(photo)
        if url.startswith("http") and url not in photos:
            photos.append(url)
        if len(photos) >= 3:
            break
    return photos


def _to_item(poi: Dict[str, Any], city: str) -> Optional[Dict[str, Any]]:
    name = _text(poi.get("name"))
    location = _parse_location(poi.get("location"))
    if not name or not location or not _is_attraction(poi):
        return None

    type_text = _text(poi.get("type"))
    category = _category(type_text)
    address = _text(poi.get("address")) or _text(poi.get("adname")) or city
    rating = _parse_rating((poi.get("biz_ext") or {}).get("rating"))
    ticket_price = _parse_ticket_price((poi.get("biz_ext") or {}).get("cost"))
    photos = _photos(poi)
    return {
        "id": _text(poi.get("id")),
        "name": name,
        "city": city,
        "address": address,
        "location": location,
        "type": type_text,
        "category": category,
        "rating": rating,
        "ticket_price": ticket_price,
        "photos": photos,
        "image_url": photos[0] if photos else "",
        "description": _description(name, category, address, rating),
        "visit_duration": _visit_duration(category),
        "source": "amap",
    }


def _is_excluded(name: Any, excluded: set[str]) -> bool:
    key = _name_key(name)
    if not key:
        return False
    for candidate in excluded:
        if key == candidate:
            return True
        # “鸡鸣寺”与“古鸡鸣寺”、“夫子庙”与“南京夫子庙”视为同一景点；
        # 要求被包含的一方至少 3 个字，避免“山/湖”等短词误伤。
        if len(candidate) >= 3 and candidate in key:
            return True
        if len(key) >= 3 and key in candidate:
            return True
    return False


def _dedupe_and_sort(items: Iterable[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    seen = set()
    unique = []
    for item in items:
        key = _name_key(item.get("name"))
        if not key:
            continue
        if any(
            key == existing
            or (len(existing) >= 3 and existing in key)
            or (len(key) >= 3 and key in existing)
            for existing in seen
        ):
            continue
        seen.add(key)
        unique.append(item)
    unique.sort(
        key=lambda item: (
            item.get("rating") or 0,
            1 if item.get("image_url") else 0,
        ),
        reverse=True,
    )
    return unique[:limit]


async def get_popular_attractions(
    city: str,
    exclude_names: Iterable[str] = (),
    limit: int = 12,
) -> List[Dict[str, Any]]:
    """查询城市热门景点，并过滤掉当前行程已有的景点。"""
    city = str(city or "").strip()
    if not city:
        return []

    excluded = {_name_key(name) for name in exclude_names if _name_key(name)}
    cache_key = f"{city}|{limit}|{','.join(sorted(excluded))}"
    cached = _CACHE.get(cache_key)
    if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
        return [dict(item) for item in cached[1]]

    settings = get_settings()
    api_key = (settings.vite_amap_web_key or "").strip()
    items: List[Dict[str, Any]] = []
    if api_key:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    _AMAP_PLACE_TEXT,
                    params={
                        "key": api_key,
                        "keywords": "景点",
                        "city": city,
                        "citylimit": "true",
                        "offset": 25,
                        "page": 1,
                        "extensions": "all",
                        "output": "JSON",
                    },
                )
                payload = response.json()
            if payload.get("status") == "1":
                for poi in payload.get("pois") or []:
                    if not isinstance(poi, dict):
                        continue
                    if _is_excluded(poi.get("name"), excluded):
                        continue
                    item = _to_item(poi, city)
                    if item:
                        items.append(item)
        except Exception as error:
            print(f"⚠️  热门景点查询失败（{city}）: {error}")

    result = _dedupe_and_sort(items, max(1, min(int(limit or 12), 24)))
    _CACHE[cache_key] = (time.time(), result)
    return [dict(item) for item in result]
