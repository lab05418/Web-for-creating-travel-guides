"""城际席别分类：按交通方式各自独立。

中国铁路 12306 的席别并不是一套通用枚举：

- 高铁/动车：二等座、一等座、特等座、商务座、无座；
- 普速火车：硬座、软座、硬卧、软卧、高级软卧、无座；
- 飞机：经济舱、超级经济舱、公务舱、头等舱（航司舱位体系）。

本模块只保存“方式 -> 可选席别/默认席别”的映射，票价系数放在
``services/transport_pricing.py``，避免模型层反向依赖服务层。
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

SEAT_TYPES_BY_MODE: Dict[str, Tuple[str, ...]] = {
    "高铁": ("二等座", "一等座", "特等座", "商务座", "无座"),
    "火车": ("硬座", "软座", "硬卧", "软卧", "高级软卧", "无座"),
    "飞机": ("经济舱", "超级经济舱", "公务舱", "头等舱"),
}

DEFAULT_SEAT_BY_MODE: Dict[str, str] = {
    "高铁": "二等座",
    "火车": "硬座",
    "飞机": "经济舱",
}

SUPPORTED_INTERCITY_MODES: Tuple[str, ...] = tuple(SEAT_TYPES_BY_MODE.keys())


def normalize_seat_type(mode: Any, value: Any = None) -> Optional[str]:
    """把席别归一到当前交通方式的有效选项。

    - 交通方式不支持独立席别（自驾/长途汽车）时返回 None；
    - 席别为空、或不属于当前方式时，回退到该方式的默认席别。
    """
    mode_text = str(mode or "").strip()
    options = SEAT_TYPES_BY_MODE.get(mode_text)
    if not options:
        return None

    seat_text = str(value or "").strip()
    if seat_text in options:
        return seat_text
    return DEFAULT_SEAT_BY_MODE[mode_text]
