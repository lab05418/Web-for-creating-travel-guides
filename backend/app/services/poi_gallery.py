"""高德 POI 实拍图库。

卡片与景点详解需要「能辨认出景点」的图片。小红书的搜索首图偶尔会命中
无关内容（例如搜钟楼出现樱花），因此优先使用高德 POI 详情里的实拍图：
高德返回的是该 POI 的官方/用户实拍，数量通常为 3 张，且可按城市消歧。

结果按「城市 + 景点名」落盘缓存，避免每次进入结果页都请求高德。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from ..config import get_settings

_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "poi_photos"
_CACHE_TTL_SECONDS = 7 * 24 * 3600
_MAX_PHOTOS = 3
_NEGATIVE_WORDS = ("地铁站", "售票", "停车场", "游客中心", "入口", "出口", "酒店", "宾馆", "公厕", "厕所")
_POSITIVE_TYPES = ("风景名胜", "博物馆", "纪念馆", "公园", "旅游景点")


def _normalize(text: Any) -> str:
    return re.sub(r"[\s·•,，、/|（）()【】\[\]《》“”\"']+", "", str(text or "").lower())


def _cache_path(name: str, city: str) -> Path:
    digest = hashlib.sha1(f"{_normalize(city)}|{_normalize(name)}".encode("utf-8")).hexdigest()[:24]
    return _CACHE_DIR / f"{digest}.json"


def _read_cache(name: str, city: str) -> Optional[List[str]]:
    path = _cache_path(name, city)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    if time.time() - float(payload.get("ts") or 0) > _CACHE_TTL_SECONDS:
        return None
    photos = payload.get("photos")
    if not isinstance(photos, list):
        return None
    return [str(item) for item in photos if str(item).startswith("https://")]


def _write_cache(name: str, city: str, photos: List[str]) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {"name": name, "city": city, "photos": photos, "ts": time.time()}
        fd, temp_path = tempfile.mkstemp(dir=str(_CACHE_DIR), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(temp_path, _cache_path(name, city))
    except Exception as exc:  # pragma: no cover
        print(f"⚠️  写入高德图库缓存失败: {exc}")


def _as_https(url: str) -> str:
    value = str(url or "").strip()
    if value.startswith("http://"):
        value = "https://" + value[len("http://") :]
    # store.is.autonavi.com 的原图接口默认返回 500px 缩略图；
    # 加 ?type=pic 可拿到 2000px+ 原图，详情大图才足够清晰。
    if "store.is.autonavi.com/showpic/" in value and "?" not in value:
        value += "?type=pic"
    return value


def _pick_poi(pois: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    query = _normalize(name)
    if not query:
        return None

    best: Optional[Dict[str, Any]] = None
    best_score = -10**9

    for poi in pois:
        if not isinstance(poi, dict):
            continue
        poi_name = str(poi.get("name") or "")
        normalized = _normalize(poi_name)
        photos = poi.get("photos") or []
        if not normalized or not isinstance(photos, list) or not photos:
            continue

        score = 0
        if normalized == query:
            score += 100
        elif query in normalized or normalized in query:
            score += 60
        else:
            # 高德对「碑林博物馆」可能先返回「西安城墙」等泛结果，名称不匹配直接淘汰
            continue

        if any(word in poi_name for word in _NEGATIVE_WORDS):
            score -= 120
        poi_type = str(poi.get("type") or "")
        if any(word in poi_type for word in _POSITIVE_TYPES):
            score += 20
        if poi.get("photos"):
            score += 10

        if score > best_score:
            best_score = score
            best = poi

    return best if best_score > 0 else None


async def _fetch_from_amap(name: str, city: str) -> List[str]:
    settings = get_settings()
    key = (settings.vite_amap_web_key or "").strip()
    if not key:
        return []

    params = {
        "key": key,
        "keywords": name,
        "city": city or "",
        "citylimit": "true",
        "extensions": "all",
        "offset": "8",
        "page": "1",
    }
    try:
        async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
            response = await client.get("https://restapi.amap.com/v3/place/text", params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        print(f"⚠️  高德 POI 图片搜索失败（{name}）: {exc}")
        return []

    if str(payload.get("status")) != "1":
        return []

    pois = payload.get("pois") or []
    if not isinstance(pois, list):
        return []

    poi = _pick_poi(pois, name)
    if not poi:
        return []

    photos: List[str] = []
    for photo in poi.get("photos") or []:
        if not isinstance(photo, dict):
            continue
        url = _as_https(photo.get("url") or "")
        if url.startswith("https://") and url not in photos:
            photos.append(url)
        if len(photos) >= _MAX_PHOTOS:
            break
    return photos


_locks: Dict[str, asyncio.Lock] = {}


def _lock_for(name: str, city: str) -> asyncio.Lock:
    key = f"{_normalize(city)}|{_normalize(name)}"
    lock = _locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _locks[key] = lock
    return lock


async def get_poi_photos(name: str, city: str = "", limit: int = _MAX_PHOTOS) -> List[str]:
    """获取 POI 实拍图；优先读缓存，miss 时请求高德并落盘。"""
    clean_name = str(name or "").strip()[:80]
    if not clean_name:
        return []
    limit = max(1, min(int(limit or _MAX_PHOTOS), 6))

    cached = _read_cache(clean_name, city)
    if cached is not None:
        return cached[:limit]

    async with _lock_for(clean_name, city):
        cached = _read_cache(clean_name, city)
        if cached is not None:
            return cached[:limit]

        photos = await _fetch_from_amap(clean_name, city)
        if photos:
            _write_cache(clean_name, city, photos)
        return photos[:limit]
