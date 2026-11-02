"""地点实时价格查询与类型推断。

高德 POI 的 ``biz_ext.cost`` 是门店/景点公开的参考消费（餐厅通常为人均，
酒店通常为参考房价，景点可能为门票），并不保证实时库存价格。这里用
Place Text / Detail 接口做一次实时查询，查不到就明确返回无价格，绝不编造。
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, Optional

import httpx

from ..config import get_settings

_CACHE_TTL_SECONDS = 10 * 60
_CACHE: Dict[str, tuple[float, Dict[str, Any]]] = {}

_HOTEL_WORDS = ("酒店", "宾馆", "旅馆", "民宿", "客栈", "度假村", "公寓")
_RESTAURANT_WORDS = (
    "餐厅", "饭店", "菜馆", "酒家", "小吃", "美食", "火锅", "烧烤",
    "面馆", "咖啡", "茶馆", "餐吧", "食堂", "料理", "烘焙", "甜品",
)
_STATION_WORDS = ("机场", "航站楼", "火车站", "高铁站", "车站", "汽车站", "码头", "地铁站")
_ATTRACTION_WORDS = (
    "景区", "景点", "公园", "博物馆", "纪念馆", "美术馆", "展览馆", "寺",
    "庙", "塔", "楼", "宫", "府", "园", "山", "湖", "街", "古镇", "遗址",
    "城墙", "陵", "祠", "故居", "广场",
)


def _normalize(text: Any) -> str:
    return re.sub(r"[\s·•,，、/|（）()【】\[\]《》“”\"']+", "", str(text or "").lower())


def _parse_money(value: Any) -> Optional[float]:
    """biz_ext.cost 可能是 '60.00'、60、[]、['60'] 或带文字。"""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, list):
        value = value[0] if value else None
    if isinstance(value, dict):
        value = value.get("cost") or value.get("price") or value.get("amount")
    if value is None:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _infer_type(text: str, fallback: str = "custom") -> str:
    haystack = str(text or "")
    if any(word in haystack for word in _HOTEL_WORDS):
        return "hotel"
    if any(word in haystack for word in _RESTAURANT_WORDS):
        return "restaurant"
    if any(word in haystack for word in _STATION_WORDS):
        return "station"
    if any(word in haystack for word in _ATTRACTION_WORDS):
        return "attraction"
    return fallback if fallback in {"hotel", "attraction", "restaurant", "station", "custom"} else "custom"


def _pick_poi(pois: list[Dict[str, Any]], name: str, address: str) -> Optional[Dict[str, Any]]:
    query = _normalize(name)
    address_query = _normalize(address)
    if not query:
        return None

    best: Optional[Dict[str, Any]] = None
    best_score = -10**9
    for poi in pois:
        if not isinstance(poi, dict):
            continue
        poi_name = str(poi.get("name") or "")
        normalized = _normalize(poi_name)
        if not normalized:
            continue
        if normalized == query:
            score = 100
        elif query in normalized or normalized in query:
            score = 60
        else:
            continue
        if address_query and normalized:
            poi_address = _normalize(poi.get("address") or "")
            if poi_address and (address_query in poi_address or poi_address in address_query):
                score += 20
        if poi.get("biz_ext") or poi.get("type"):
            score += 5
        if score > best_score:
            best_score = score
            best = poi
    return best if best_score > 0 else None


async def _request_place_text(name: str, city: str) -> list[Dict[str, Any]]:
    settings = get_settings()
    key = (settings.vite_amap_web_key or "").strip()
    if not key:
        return []
    params = {
        "key": key,
        "keywords": name[:80],
        "city": city or "",
        "citylimit": "true",
        "extensions": "all",
        "offset": "8",
        "page": "1",
    }
    try:
        async with httpx.AsyncClient(timeout=6, trust_env=False) as client:
            response = await client.get("https://restapi.amap.com/v3/place/text", params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        print(f"⚠️  地点价格查询失败（{name}）: {exc}")
        return []
    if str(payload.get("status")) != "1":
        return []
    pois = payload.get("pois") or []
    return [item for item in pois if isinstance(item, dict)]


async def _request_place_detail(poi_id: str) -> Optional[Dict[str, Any]]:
    settings = get_settings()
    key = (settings.vite_amap_web_key or "").strip()
    if not key or not poi_id:
        return None
    try:
        async with httpx.AsyncClient(timeout=6, trust_env=False) as client:
            response = await client.get(
                "https://restapi.amap.com/v3/place/detail",
                params={"key": key, "id": poi_id, "extensions": "all"},
            )
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        print(f"⚠️  地点详情查询失败（{poi_id}）: {exc}")
        return None
    if str(payload.get("status")) != "1":
        return None
    pois = payload.get("pois") or []
    return pois[0] if pois and isinstance(pois[0], dict) else None


def _build_result(
    poi: Optional[Dict[str, Any]],
    *,
    name: str,
    note: str,
    address: str,
    fallback_type: str,
    poi_id: str,
) -> Dict[str, Any]:
    if not poi:
        return {
            "price": None,
            "currency": "CNY",
            "price_kind": "unknown",
            "price_source": "unavailable",
            "poi_id": poi_id or None,
            "matched_name": "",
            "inferred_type": _infer_type(f"{name} {note} {address}", fallback_type),
            "raw_type": "",
            "has_price": False,
        }

    raw_type = str(poi.get("type") or "")
    inferred = _infer_type(f"{raw_type} {name} {note} {address}", fallback_type)
    biz = poi.get("biz_ext") if isinstance(poi.get("biz_ext"), dict) else {}
    cost = _parse_money(biz.get("cost"))
    price_kind = {
        "hotel": "per_night",
        "restaurant": "per_person",
        "attraction": "ticket",
    }.get(inferred, "unknown")
    return {
        "price": round(cost, 2) if cost is not None else None,
        "currency": "CNY",
        "price_kind": price_kind,
        "price_source": "amap" if cost is not None else "unavailable",
        "poi_id": str(poi.get("id") or poi_id or "") or None,
        "matched_name": str(poi.get("name") or ""),
        "inferred_type": inferred,
        "raw_type": raw_type,
        "has_price": cost is not None,
        "rating": biz.get("rating") if isinstance(biz, dict) else None,
    }


async def lookup_place_price(
    *,
    name: str,
    city: str = "",
    address: str = "",
    note: str = "",
    place_type: str = "custom",
    poi_id: str = "",
) -> Dict[str, Any]:
    """实时查询地点价格；失败/无价格时返回 price=None，不抛异常阻断添加。"""
    clean_name = str(name or "").strip()[:80]
    clean_city = str(city or "").strip()
    cache_key = f"{_normalize(clean_city)}|{_normalize(clean_name)}|{poi_id or ''}|{place_type}"
    now = time.time()
    cached = _CACHE.get(cache_key)
    if cached and now - cached[0] < _CACHE_TTL_SECONDS:
        return dict(cached[1])

    poi: Optional[Dict[str, Any]] = None
    if poi_id:
        poi = await _request_place_detail(poi_id)
    if not poi:
        pois = await _request_place_text(clean_name, clean_city)
        poi = _pick_poi(pois, clean_name, address)

    result = _build_result(
        poi,
        name=clean_name,
        note=note,
        address=address,
        fallback_type=place_type,
        poi_id=poi_id,
    )
    _CACHE[cache_key] = (now, dict(result))
    return result
