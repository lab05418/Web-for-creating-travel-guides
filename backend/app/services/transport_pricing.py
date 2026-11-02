"""城际交通票价估算（12306 里程计价规则）。

设计目标：
- 高铁、火车、飞机共用同一套“里程阶梯 + 席别系数”公式，避免三个入口各算一套；
- 票价按“出发地 → 各城市 → 出发地”的往返/联程分段计算，再逐段取整相加；
- 城际距离优先使用行程中景点/酒店的坐标，缺失时用高德地理编码补全；
- 只做参考估算，不冒充 12306 或航司的实时余票/实时成交价。

12306 的公布票价并不是一条简单的固定单价，而是随里程递远递减。这里采用
分档边际里程费率（200km 内基准、200-500km 92%、500-1000km 85%、
1000-2000km 78%、2000km 以上 72%），再用“当前交通方式”的席别系数换算。
高铁、火车、飞机各自有独立的席别分类，详见 ``models/seat_types.py``；
三者的共同点是使用同一套里程阶梯，而不是共用同一组席别名称。
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import httpx

from ..config import get_settings
from ..models.seat_types import normalize_seat_type

# 各交通方式独立席别系数。基准分别是：
# 高铁二等座、火车硬座、飞机经济舱。
SEAT_MULTIPLIERS_BY_MODE: Dict[str, Dict[str, float]] = {
    "高铁": {
        "二等座": 1.0,
        "一等座": 1.6,
        "特等座": 2.4,
        "商务座": 3.0,
        "无座": 1.0,
    },
    "火车": {
        "硬座": 1.0,
        "软座": 1.5,
        "硬卧": 1.8,
        "软卧": 2.8,
        "高级软卧": 4.0,
        "无座": 1.0,
    },
    "飞机": {
        "经济舱": 1.0,
        "超级经济舱": 1.3,
        "公务舱": 2.5,
        "头等舱": 4.0,
    },
}

# 各交通方式的基准里程费率（元/公里）与最低票价（元）。
# 高铁按 G/D 二等座公布票价量级；火车按普速硬座量级；飞机按经济舱参考价量级。
MODE_RATES: Dict[str, float] = {
    "高铁": 0.46,
    "火车": 0.15,
    "飞机": 0.65,
}
MODE_MIN_FARES: Dict[str, int] = {
    "高铁": 30,
    "火车": 10,
    "飞机": 200,
}
# 铁路线路通常比直线距离绕行；飞机按大圆距离。
MODE_ROUTE_FACTORS: Dict[str, float] = {
    "高铁": 1.15,
    "火车": 1.20,
    "飞机": 1.00,
}

# (里程上限 km, 该段边际费率系数)，最后一段用 None 表示无上限。
DISTANCE_TIERS: Tuple[Tuple[Optional[float], float], ...] = (
    (200.0, 1.00),
    (500.0, 0.92),
    (1000.0, 0.85),
    (2000.0, 0.78),
    (None, 0.72),
)

_CITY_COORDS: Dict[str, Tuple[float, float]] = {
    "北京": (116.4074, 39.9042),
    "上海": (121.4737, 31.2304),
    "广州": (113.2644, 23.1291),
    "深圳": (114.0579, 22.5431),
    "成都": (104.0665, 30.5728),
    "杭州": (120.1551, 30.2741),
    "南京": (118.7969, 32.0603),
    "西安": (108.9398, 34.3416),
    "重庆": (106.5516, 29.5630),
    "武汉": (114.3055, 30.5928),
    "长沙": (112.9388, 28.2282),
    "苏州": (120.5853, 31.2989),
    "天津": (117.2008, 39.0842),
    "青岛": (120.3826, 36.0671),
    "厦门": (118.0894, 24.4798),
    "昆明": (102.8329, 24.8801),
    "大理": (100.2676, 25.6065),
    "丽江": (100.2330, 26.8550),
    "三亚": (109.5080, 18.2479),
    "海口": (110.1983, 20.0440),
    "桂林": (110.2902, 25.2736),
    "贵阳": (106.6302, 26.6477),
    "哈尔滨": (126.6424, 45.7567),
    "沈阳": (123.4315, 41.8057),
    "大连": (121.6147, 38.9140),
    "济南": (117.1201, 36.6512),
    "郑州": (113.6254, 34.7466),
    "合肥": (117.2272, 31.8206),
    "福州": (119.2965, 26.0745),
    "南昌": (115.8582, 28.6820),
    "南宁": (108.3669, 22.8170),
    "兰州": (103.8343, 36.0611),
    "西宁": (101.7782, 36.6171),
    "银川": (106.2309, 38.4872),
    "乌鲁木齐": (87.6168, 43.8256),
    "拉萨": (91.1322, 29.6604),
    "呼和浩特": (111.7492, 40.8426),
    "太原": (112.5489, 37.8706),
    "石家庄": (114.5149, 38.0428),
    "宁波": (121.5503, 29.8746),
    "无锡": (120.3119, 31.4912),
    "常州": (119.9741, 31.8112),
    "扬州": (119.4129, 32.3942),
    "洛阳": (112.4540, 34.6197),
    "开封": (114.3076, 34.7971),
    "敦煌": (94.6618, 40.1421),
    "张家界": (110.4792, 29.1171),
    "黄山": (118.3376, 29.7147),
    "秦皇岛": (119.6005, 39.9354),
    "承德": (117.9627, 40.9542),
    "泉州": (118.6757, 24.8741),
    "珠海": (113.5767, 22.2707),
    "佛山": (113.1214, 23.0215),
    "东莞": (113.7518, 23.0207),
    "温州": (120.6994, 27.9949),
    "绍兴": (120.5802, 30.0303),
    "嘉兴": (120.7555, 30.7461),
    "镇江": (119.4250, 32.1877),
    "南通": (120.8943, 31.9802),
    "烟台": (121.4479, 37.4638),
    "威海": (122.1204, 37.5131),
    "大同": (113.3001, 40.0768),
    "延安": (109.4898, 36.5853),
    "乐山": (103.7656, 29.5521),
    "遵义": (106.9272, 27.7257),
    "北海": (109.1193, 21.4813),
    "西双版纳": (100.7979, 22.0017),
    "香格里拉": (99.7065, 27.8269),
    "九寨沟": (103.9186, 33.2523),
    "张掖": (100.4498, 38.9259),
    "包头": (109.8403, 40.6574),
    "鄂尔多斯": (109.7813, 39.6083),
    "吉林": (126.5496, 43.8378),
    "长春": (125.3235, 43.8171),
    "唐山": (118.1802, 39.6305),
    "保定": (115.4646, 38.8738),
    "徐州": (117.1848, 34.2618),
    "连云港": (119.2216, 34.5967),
    "芜湖": (118.4331, 31.3525),
    "九江": (115.9928, 29.7120),
    "赣州": (114.9350, 25.8311),
    "湛江": (110.3594, 21.2707),
    "吐鲁番": (89.1841, 42.9476),
    "喀什": (75.9898, 39.4677),
    "伊宁": (81.3245, 43.9169),
    "阿勒泰": (88.1413, 47.8449),
    "日喀则": (88.8851, 29.2675),
    "林芝": (94.3615, 29.6491),
}

# 目的地城市在行程里可能写成“西安市”“中国-西安”，统一成简称再查表/地理编码。
_CITY_ALIASES: Dict[str, str] = {
    "北京市": "北京",
    "上海市": "上海",
    "广州市": "广州",
    "深圳市": "深圳",
    "成都市": "成都",
    "杭州市": "杭州",
    "南京市": "南京",
    "西安市": "西安",
    "重庆市": "重庆",
    "武汉市": "武汉",
    "长沙市": "长沙",
    "苏州市": "苏州",
    "天津市": "天津",
    "青岛市": "青岛",
    "厦门市": "厦门",
    "昆明市": "昆明",
    "大连市": "大连",
    "哈尔滨市": "哈尔滨",
    "沈阳市": "沈阳",
    "济南市": "济南",
    "郑州市": "郑州",
    "合肥市": "合肥",
    "福州市": "福州",
    "南昌市": "南昌",
    "南宁市": "南宁",
    "兰州市": "兰州",
    "西宁市": "西宁",
    "银川市": "银川",
    "乌鲁木齐市": "乌鲁木齐",
    "拉萨市": "拉萨",
    "呼和浩特市": "呼和浩特",
    "太原市": "太原",
    "石家庄市": "石家庄",
    "宁波市": "宁波",
}
_CITY_CACHE: Dict[str, Optional[Tuple[float, float]]] = {}


@dataclass(frozen=True)
class TransportLeg:
    """一段城际行程。"""

    origin: str
    destination: str
    distance_km: float
    fare: int


@dataclass(frozen=True)
class TransportQuote:
    """一次完整城际行程的计价结果。"""

    mode: str
    seat_type: str
    distance_km: float
    ticket_total: int
    legs: Tuple[TransportLeg, ...] = field(default_factory=tuple)


def normalize_city_name(value: Any) -> str:
    """去掉国家/省份前缀和“市”后缀，便于查坐标表。"""
    text = str(value or "").strip()
    text = re.sub(r"^中国[-—/·\s]*", "", text)
    text = text.split("-")[-1].strip() if "-" in text else text
    if text in _CITY_ALIASES:
        return _CITY_ALIASES[text]
    if text.endswith("市") and text[:-1] in _CITY_COORDS:
        return text[:-1]
    return text


def haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """两点经纬度的大圆距离（公里）。"""
    lng1, lat1 = float(a[0]), float(a[1])
    lng2, lat2 = float(b[0]), float(b[1])
    radius = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    h = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * radius * math.asin(min(1.0, math.sqrt(h)))


def distance_fare(distance_km: float, mode: str) -> float:
    """按 12306 式递远递减里程阶梯计算基准席别票价（未乘席别系数）。"""
    if mode not in MODE_RATES:
        return 0.0
    distance = max(0.0, float(distance_km))
    if distance <= 0:
        return 0.0

    rate = MODE_RATES[mode]
    total = 0.0
    lower = 0.0
    for upper, factor in DISTANCE_TIERS:
        if distance <= lower:
            break
        boundary = distance if upper is None else min(distance, upper)
        segment = max(0.0, boundary - lower)
        total += segment * rate * factor
        lower = boundary
        if upper is not None and distance <= upper:
            break
    return total


def calculate_ticket_price(
    distance_km: float,
    mode: str,
    seat_type: Optional[str] = None,
) -> Optional[int]:
    """计算单段票价；不支持的交通方式返回 None。

    席别必须属于当前交通方式；不匹配时回退到该方式的默认席别。
    """
    if mode not in MODE_RATES:
        return None
    normalized_seat = normalize_seat_type(mode, seat_type)
    if normalized_seat is None:
        return None
    distance = max(0.0, float(distance_km))
    if distance <= 0:
        return 0
    base_fare = int(round(max(float(MODE_MIN_FARES[mode]), distance_fare(distance, mode))))
    seat_multiplier = SEAT_MULTIPLIERS_BY_MODE[mode][normalized_seat]
    return int(round(base_fare * seat_multiplier))


def build_city_sequence(origin: str, cities: Sequence[str]) -> List[str]:
    """构建实际需要计价的站点序列。

    - 有出发地：出发地 → 各城市 → 出发地（往返各一次）；
    - 无出发地但多城市：城市1 → … → 城市N → … → 城市1（反程补齐）；
    - 单城市：没有城际段。
    """
    origin_text = str(origin or "").strip()
    city_list = [str(city or "").strip() for city in cities if str(city or "").strip()]
    if not origin_text:
        if len(city_list) <= 1:
            return city_list
        # A,B,C -> A,B,C,B,A；A,B -> A,B,A；保证每段往、返各计一次。
        return [*city_list, *reversed(city_list[:-1])]
    return [origin_text, *city_list, origin_text]


def calculate_quote(
    origin: str,
    cities: Sequence[str],
    mode: str,
    seat_type: Optional[str],
    coordinates: Dict[str, Tuple[float, float]],
) -> Optional[TransportQuote]:
    """用给定城市坐标计算完整城际报价（纯函数，便于离线测试）。"""
    if mode not in MODE_RATES:
        return None
    normalized_seat = normalize_seat_type(mode, seat_type)
    if normalized_seat is None:
        return None

    sequence = build_city_sequence(origin, cities)
    if len(sequence) < 2:
        return TransportQuote(
            mode=mode,
            seat_type=normalized_seat,
            distance_km=0.0,
            ticket_total=0,
        )

    route_factor = MODE_ROUTE_FACTORS[mode]
    legs: List[TransportLeg] = []
    for start, end in zip(sequence, sequence[1:]):
        start_coord = coordinates.get(start) or coordinates.get(normalize_city_name(start))
        end_coord = coordinates.get(end) or coordinates.get(normalize_city_name(end))
        if not start_coord or not end_coord:
            return None
        distance = haversine_km(start_coord, end_coord) * route_factor
        fare = calculate_ticket_price(distance, mode, normalized_seat)
        if fare is None:
            return None
        if distance < 1 and fare <= 0:
            continue
        legs.append(
            TransportLeg(
                origin=start,
                destination=end,
                distance_km=round(distance, 1),
                fare=fare,
            )
        )

    return TransportQuote(
        mode=mode,
        seat_type=normalized_seat,
        distance_km=round(sum(leg.distance_km for leg in legs), 1),
        ticket_total=sum(leg.fare for leg in legs),
        legs=tuple(legs),
    )


def _read_value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _location_tuple(value: Any) -> Optional[Tuple[float, float]]:
    longitude = _read_value(value, "longitude")
    latitude = _read_value(value, "latitude")
    try:
        lng = float(longitude)
        lat = float(latitude)
    except (TypeError, ValueError):
        return None
    if not (-180 <= lng <= 180 and -90 <= lat <= 90):
        return None
    return lng, lat


def collect_plan_city_coordinates(plan: Any) -> Dict[str, Tuple[float, float]]:
    """从行程的景点/酒店坐标估算各城市中心，避免额外网络请求。"""
    buckets: Dict[str, List[Tuple[float, float]]] = {}
    days = _read_value(plan, "days", []) or []
    for day in days:
        city = str(_read_value(day, "city", "") or "").strip()
        if not city:
            continue
        points: List[Tuple[float, float]] = []
        for attraction in _read_value(day, "attractions", []) or []:
            point = _location_tuple(_read_value(attraction, "location", None))
            if point:
                points.append(point)
        hotel = _read_value(day, "hotel", None)
        if hotel:
            point = _location_tuple(_read_value(hotel, "location", None))
            if point:
                points.append(point)
        if points:
            buckets.setdefault(city, []).extend(points)

    return {
        city: (
            sum(point[0] for point in points) / len(points),
            sum(point[1] for point in points) / len(points),
        )
        for city, points in buckets.items()
        if points
    }


def _match_plan_coordinate(
    city: str,
    plan_coords: Dict[str, Tuple[float, float]],
) -> Optional[Tuple[float, float]]:
    normalized = normalize_city_name(city)
    if normalized in plan_coords:
        return plan_coords[normalized]
    for name, coord in plan_coords.items():
        if normalize_city_name(name) == normalized:
            return coord
    return None


async def geocode_city(city: str) -> Optional[Tuple[float, float]]:
    """用高德地理编码补齐坐标；失败时回退到内置主要城市表。"""
    normalized = normalize_city_name(city)
    if normalized in _CITY_CACHE:
        return _CITY_CACHE[normalized]

    settings = get_settings()
    api_key = (settings.vite_amap_web_key or "").strip()
    if api_key:
        try:
            async with httpx.AsyncClient(timeout=6) as client:
                response = await client.get(
                    "https://restapi.amap.com/v3/geocode/geo",
                    params={
                        "key": api_key,
                        "address": normalized,
                        "output": "JSON",
                    },
                )
                payload = response.json()
            geocodes = payload.get("geocodes") or []
            if payload.get("status") == "1" and geocodes:
                location = str(geocodes[0].get("location") or "")
                if "," in location:
                    lng_text, lat_text = location.split(",", 1)
                    coord = (float(lng_text), float(lat_text))
                    _CITY_CACHE[normalized] = coord
                    return coord
        except Exception as error:
            print(f"⚠️  城际票价地理编码失败（{normalized}）: {error}")

    fallback = _CITY_COORDS.get(normalized)
    _CITY_CACHE[normalized] = fallback
    return fallback


async def estimate_intercity_quote(plan: Any, request: Any) -> Optional[TransportQuote]:
    """按请求的交通方式/席别与行程城市，估算完整城际票价。"""
    mode = str(_read_value(request, "intercity_transportation", "") or "").strip()
    if mode not in MODE_RATES:
        return None

    seat_type = normalize_seat_type(
        mode,
        _read_value(request, "intercity_seat_type", None),
    )
    if seat_type is None:
        return None
    origin = str(_read_value(request, "origin", "") or "").strip()
    city_stays = _read_value(request, "cities", []) or []
    cities = [
        str(_read_value(stay, "city", "") or "").strip()
        for stay in city_stays
        if str(_read_value(stay, "city", "") or "").strip()
    ]
    if not cities:
        single_city = str(_read_value(request, "city", "") or "").strip()
        if single_city:
            cities = [single_city]
    if not cities:
        return None

    # 单城市且无出发地时不存在城际段，直接返回 0，避免无意义的地理编码。
    if not origin and len(cities) <= 1:
        return TransportQuote(
            mode=mode,
            seat_type=seat_type,
            distance_km=0.0,
            ticket_total=0,
        )

    plan_coords = collect_plan_city_coordinates(plan)
    coordinates: Dict[str, Tuple[float, float]] = {}
    for city in cities:
        coord = _match_plan_coordinate(city, plan_coords)
        if coord:
            coordinates[city] = coord
        else:
            geocoded = await geocode_city(city)
            if geocoded:
                coordinates[city] = geocoded

    if origin:
        coord = _match_plan_coordinate(origin, plan_coords)
        if coord:
            coordinates[origin] = coord
        else:
            geocoded = await geocode_city(origin)
            if geocoded:
                coordinates[origin] = geocoded

    return calculate_quote(origin, cities, mode, seat_type, coordinates)
