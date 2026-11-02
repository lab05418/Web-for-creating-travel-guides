"""统一地图服务调度层

全部走高德地图 Web 服务完成地理编码。

用法:
    from ..services.map_dispatcher import geocode_unified

    location = geocode_unified("故宫", "北京")
"""

from typing import Optional


def geocode_unified(address: str, city: str, *, address_zh: str = "", address_en: str = "") -> Optional[dict]:
    """统一地理编码接口，成功返回 {"longitude": float, "latitude": float}，失败返回 None。

    使用高德地图进行地理编码：
    - 高德地图: 优先使用中文地址 (address_zh)，对中文地名识别更准确
    - address_en 仅为兼容既有调用方保留，不再参与编码

    注意：失败返回 None，不能伪造默认坐标。

    Args:
        address: 默认地址（任意语言，作为兜底）
        city: 城市名称
        address_zh: 中文地址（优先用于高德地图）
        address_en: 英文地址（保留参数，仅作兼容）
    """
    amap_address = address_zh or address
    from .xhs_service import _geocode_amap_raw  # noqa: delay import
    return _geocode_amap_raw(amap_address, city)
