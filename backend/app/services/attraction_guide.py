"""景点深度导览服务。

为行程概览中的景点提供「历史背景 + 有趣好玩 + 实用提示」的详细介绍。

内容优先级：
1. 本地精选内容（``app/data/attraction_guides.json``），覆盖常见目的地，离线可用；
2. 本地缓存（``backend/data/guides``），避免同一景点重复调用模型；
3. LLM 实时生成（仅在本地没有内容时触发）；
4. 兜底文案：模型不可用时，用行程里的简介整理出可读的介绍。

该模块只读取 LLM 配置，不会修改任何 DeepSeek 配置。
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

_SCHEMA_VERSION = 1
_MAX_FUN_FACTS = 5
_MAX_TIPS = 4
# 兜底文案只缓存 10 分钟：既能避免模型抖动时反复等待，又不会永久挡住后续 AI 生成。
_FALLBACK_TTL_SECONDS = 10 * 60

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_GUIDE_CACHE_DIR = _BACKEND_DIR / "data" / "guides"
_SEED_FILE = Path(__file__).resolve().parents[1] / "data" / "attraction_guides.json"

_seed_index: Optional[Dict[str, Dict[str, Any]]] = None
_locks: Dict[str, asyncio.Lock] = {}


# ---------------------------------------------------------------------------
# 文本与本地精选
# ---------------------------------------------------------------------------


def _normalize(text: Any) -> str:
    """用于匹配的轻量归一化：去空白、括号与常见分隔符。"""
    value = str(text or "").strip().lower()
    return re.sub(r"[\s·•,，、/|（）()【】\[\]《》“”\"']+", "", value)


def _load_seed_index() -> Dict[str, Dict[str, Any]]:
    global _seed_index
    if _seed_index is not None:
        return _seed_index

    index: Dict[str, Dict[str, Any]] = {}
    try:
        with open(_SEED_FILE, "r", encoding="utf-8") as handle:
            entries = json.load(handle)
    except Exception as exc:  # pragma: no cover - 文件缺失时静默降级
        print(f"⚠️  读取景点精选内容失败，将使用在线生成: {exc}")
        entries = []

    if isinstance(entries, list):
        for entry in entries:
            if not isinstance(entry, dict) or not entry.get("name"):
                continue
            keys = [entry.get("name"), *(entry.get("aliases") or [])]
            for key in keys:
                normalized = _normalize(key)
                if normalized:
                    index[normalized] = entry
    _seed_index = index
    return index


def _find_seed(name: str, city: str) -> Optional[Dict[str, Any]]:
    index = _load_seed_index()
    key = _normalize(name)
    if not key:
        return None

    entry = index.get(key)
    if entry is None:
        # 允许「西安城墙（永宁门）」这类带后缀的名称命中「西安城墙」
        for candidate, value in index.items():
            if len(candidate) >= 2 and (candidate in key or key in candidate):
                entry = value
                break

    if entry is None:
        return None

    seed_city = _normalize(entry.get("city"))
    requested_city = _normalize(city)
    if seed_city and requested_city and seed_city not in requested_city and requested_city not in seed_city:
        # 同名景点（例如北京钟楼）不能误用西安的内容
        return None
    return entry


def _copy_seed(entry: Dict[str, Any], requested_name: str) -> Dict[str, Any]:
    return {
        "name": requested_name or entry.get("name", ""),
        "city": entry.get("city", ""),
        "overview": entry.get("overview", ""),
        "history": entry.get("history", ""),
        "fun_facts": list(entry.get("fun_facts") or []),
        "tips": list(entry.get("tips") or []),
        "source": "curated",
    }


# ---------------------------------------------------------------------------
# 缓存
# ---------------------------------------------------------------------------


def _cache_key(name: str, city: str) -> str:
    raw = f"{_normalize(city)}|{_normalize(name)}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:24]


def _cache_path(key: str) -> Path:
    return _GUIDE_CACHE_DIR / f"{key}.json"


def _read_cache(key: str) -> Optional[Dict[str, Any]]:
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        return None
    if not isinstance(payload, dict) or payload.get("schema_version") != _SCHEMA_VERSION:
        return None
    guide = payload.get("guide")
    if not isinstance(guide, dict) or not guide.get("history"):
        return None
    guide["source"] = guide.get("source") or "ai"
    if guide.get("source") == "fallback":
        age = time.time() - float(payload.get("ts") or 0)
        if age > _FALLBACK_TTL_SECONDS:
            return None
    return guide


def _write_cache(key: str, guide: Dict[str, Any]) -> None:
    try:
        _GUIDE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": _SCHEMA_VERSION,
            "ts": time.time(),
            "guide": guide,
        }
        fd, temp_path = tempfile.mkstemp(dir=str(_GUIDE_CACHE_DIR), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(temp_path, _cache_path(key))
    except Exception as exc:  # pragma: no cover - 缓存失败不影响本次返回
        print(f"⚠️  写入景点导览缓存失败: {exc}")


# ---------------------------------------------------------------------------
# LLM 生成
# ---------------------------------------------------------------------------


def _llm_config() -> Dict[str, Any]:
    settings = get_settings()
    api_key = (
        settings.openai_api_key
        or os.getenv("LLM_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    )
    base_url = (
        settings.openai_base_url
        or os.getenv("LLM_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or "https://api.openai.com/v1"
    )
    model = (
        settings.openai_model
        or os.getenv("LLM_MODEL_ID")
        or os.getenv("OPENAI_MODEL")
        or "gpt-4"
    )
    timeout = int(os.getenv("LLM_TIMEOUT", "90"))
    return {
        "api_key": str(api_key).strip(),
        "base_url": str(base_url).rstrip("/"),
        "model": str(model).strip(),
        "timeout": max(15, min(timeout, 120)),
    }


_GUIDE_SYSTEM_PROMPT = """你是一位资深人文旅行编辑，擅长把历史讲得准确、把细节讲得好玩。
你只为一座景点撰写中文导览，内容要像当地朋友在耳边讲解，而不是百科词条复述。
要求：
1. 只使用可靠的史实与广泛流传的说法；不确定的年代、数字、票价不要编造。
2. 不要写成营销软文，不要出现“必去”“绝美”“打卡”等空泛词汇。
3. 语言自然、有画面感，可以写具体的建筑细节、人物故事、本地人的玩法。"""


def _build_guide_prompt(
    name: str,
    city: str,
    address: str,
    description: str,
    category: str,
) -> str:
    return f"""请为下面这座景点写一份中文深度导览，输出严格 JSON。

景点名称：{name}
所在城市：{city or "未知"}
地址：{address or "未知"}
行程中的简介：{description or "无"}
景点类别：{category or "景点"}

JSON 字段要求：
- overview：50—90 字的整体印象，要有画面感，不要重复简介。
- history：150—260 字的历史背景，讲清年代、沿革、关键人物或事件；不确定的细节宁可不写。
- fun_facts：3—5 条“有趣好玩”的细节，每条 20—50 字；可以写传说、冷知识、建筑巧思、本地玩法、最佳拍照点，但不要编造。
- tips：2—3 条实用提示，每条 15—40 字；涉及门票、开放时间、预约等不确定信息时，用“以景区公告为准”兜底。

只输出一个 JSON 对象，形如：
{{"overview": "...", "history": "...", "fun_facts": ["...", "..."], "tips": ["...", "..."]}}
不要输出 Markdown 代码块，不要输出 JSON 以外的任何文字。"""


def _parse_json_object(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        payload = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _as_clean_list(value: Any, limit: int, max_len: int = 400) -> List[str]:
    if isinstance(value, str):
        parts = re.split(r"[\n；;]+", value)
    elif isinstance(value, list):
        parts = value
    else:
        parts = []
    result: List[str] = []
    for item in parts:
        text = str(item or "").strip()
        text = re.sub(r"^[-*•\d.、\s]+", "", text)
        if not text:
            continue
        result.append(text[:max_len])
        if len(result) >= limit:
            break
    return result


def _normalize_guide(payload: Dict[str, Any], name: str, city: str) -> Optional[Dict[str, Any]]:
    overview = str(payload.get("overview") or "").strip()
    history = str(payload.get("history") or "").strip()
    fun_facts = _as_clean_list(payload.get("fun_facts"), _MAX_FUN_FACTS)
    tips = _as_clean_list(payload.get("tips"), _MAX_TIPS)

    if len(history) < 40:
        return None
    if not overview:
        overview = history[:80]
    if not fun_facts:
        fun_facts = ["先别急着拍照，绕着建筑走一圈，很多细节都藏在侧面和背面。"]
    if not tips:
        tips = ["开放时间与预约要求以景区当天公告为准。"]

    return {
        "name": name,
        "city": city,
        "overview": overview[:400],
        "history": history[:1200],
        "fun_facts": fun_facts,
        "tips": tips,
        "source": "ai",
    }


async def _generate_with_llm(
    name: str,
    city: str,
    address: str,
    description: str,
    category: str,
) -> Optional[Dict[str, Any]]:
    config = _llm_config()
    if not config["api_key"]:
        return None

    # DeepSeek 推理型模型默认会先生成长思维链（实测 1300–1500 reasoning tokens），
    # 既拖慢 10s+，又容易把 max_tokens 吃光导致 finish=length / 空 content。
    # 景点导览属于结构化短文案，关掉 thinking 后实测 14s → 5s，且 JSON 更稳定。
    attempts = (
        {"max_tokens": 2000, "temperature": 0.6, "thinking": {"type": "disabled"}},
        # 兼容不支持 thinking 字段的 OpenAI 兼容端点：第二次不带该参数
        {"max_tokens": 4000, "temperature": 0.3},
    )
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_key']}",
    }

    for index, tuning in enumerate(attempts, start=1):
        payload = {
            "model": config["model"],
            "messages": [
                {"role": "system", "content": _GUIDE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _build_guide_prompt(name, city, address, description, category),
                },
            ],
            **tuning,
            "response_format": {"type": "json_object"},
        }
        try:
            async with httpx.AsyncClient(timeout=config["timeout"], trust_env=False) as client:
                response = await client.post(
                    f"{config['base_url']}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
            choice = (data.get("choices") or [{}])[0]
            content = (choice.get("message") or {}).get("content") or ""
            finish_reason = choice.get("finish_reason")
            parsed = _parse_json_object(content)
            if parsed:
                guide = _normalize_guide(parsed, name, city)
                if guide:
                    return guide
                print(f"⚠️  景点导览内容不合格（history 过短）: {name}")
            else:
                print(
                    f"⚠️  景点导览 JSON 解析失败（第{index}次，finish={finish_reason}，"
                    f"输出 {len(content)} 字）: {name}"
                )
        except httpx.TimeoutException:
            print(f"⚠️  景点导览生成超时（第{index}次）: {name}")
        except httpx.HTTPStatusError as exc:
            print(f"⚠️  景点导览生成失败: HTTP {exc.response.status_code}（第{index}次）")
        except Exception as exc:
            print(f"⚠️  景点导览生成异常: {exc}（第{index}次）")
    return None


# ---------------------------------------------------------------------------
# 兜底内容
# ---------------------------------------------------------------------------


_CATEGORY_ANGLE = {
    "博物馆": "先找到镇馆之宝，再回头看它旁边的时代背景，参观路线会清晰很多。",
    "历史古迹": "留意建筑的中轴线、台阶和屋檐，古人的等级与审美都藏在这些细节里。",
    "特色街区": "主街之外的两三条小巷，往往才是本地人日常消费的地方。",
    "自然风光": "同一处风景在清晨、正午和日落时完全不同，条件允许的话多留一会儿。",
    "公园": "避开正门的人流，从侧门进去通常更安静，也更容易看到本地人的日常。",
}


def _fallback_guide(
    name: str,
    city: str,
    address: str,
    description: str,
    category: str,
) -> Dict[str, Any]:
    desc = (description or "").strip()
    if desc and desc[-1] not in "。！？!?":
        desc += "。"
    location = address or city or "行程所列位置"
    overview = desc or f"{name}是本次行程中的一站，适合放慢脚步，看看它和这座城市的关系。"
    history = (
        f"{name}位于{location}。{desc}"
        "关于更完整的历史沿革、建造年代与人物故事，建议以景区官方介绍、现场展牌或讲解为准；"
        "出发前也可以花几分钟查一查它的来历，逛起来会更有代入感。"
    )
    angle = _CATEGORY_ANGLE.get(category, "先在外围看整体，再走进内部看细节，通常比直接扎进人群更有收获。")
    fun_facts = [
        angle,
        "把到访时间放在清晨刚开门或傍晚亮灯前后，人少、光线也更好。",
        "入口处的导览图值得拍一张，标出出口和下一站方向，能少走不少回头路。",
        "如果遇到讲解团，不妨跟在后面听十分钟，常有展牌上没有的故事。",
    ]
    tips = [
        "开放时间、门票与预约要求以景区当天公告为准。",
        "旺季建议提前预约，并给安检、排队留出余量。",
        "与当天下一站尽量安排在同一片区域，减少往返。",
    ]
    return {
        "name": name,
        "city": city,
        "overview": overview[:400],
        "history": history[:1200],
        "fun_facts": fun_facts,
        "tips": tips,
        "source": "fallback",
    }


# ---------------------------------------------------------------------------
# 对外入口
# ---------------------------------------------------------------------------


def _lock_for(key: str) -> asyncio.Lock:
    lock = _locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _locks[key] = lock
    return lock


async def get_attraction_guide(
    name: str,
    city: str = "",
    address: str = "",
    description: str = "",
    category: str = "",
) -> Dict[str, Any]:
    """获取景点深度导览；任何异常都会降级为可展示的兜底内容。"""
    clean_name = str(name or "").strip()[:80]
    if not clean_name:
        return _fallback_guide("这处景点", city, address, description, category)

    started = time.perf_counter()
    seed = _find_seed(clean_name, city)
    if seed:
        return _copy_seed(seed, clean_name)

    key = _cache_key(clean_name, city)
    cached = _read_cache(key)
    if cached:
        return cached

    async with _lock_for(key):
        cached = _read_cache(key)
        if cached:
            return cached

        guide = await _generate_with_llm(
            clean_name,
            city,
            address,
            description,
            category,
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if guide:
            _write_cache(key, guide)
            print(f"[GUIDE] {clean_name} source=ai {elapsed_ms}ms")
            return guide
        print(f"[GUIDE] {clean_name} source=fallback {elapsed_ms}ms")

    # 兜底文案也写入短 TTL 缓存，避免网络抖动时同一景点反复等待 10s 以上。
    fallback = _fallback_guide(clean_name, city, address, description, category)
    _write_cache(key, fallback)
    return fallback
