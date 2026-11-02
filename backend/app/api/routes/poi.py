"""POI相关API路由"""

import asyncio

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import List, Optional
from xml.sax.saxutils import escape as xml_escape
from ...services.amap_service import get_amap_service

router = APIRouter(prefix="/poi", tags=["POI"])


def _placeholder_image_svg(label: str) -> bytes:
    """图片不可用时返回的深色占位图，避免浏览器显示破图图标。"""
    text = xml_escape((label or "景点图片")[:24])
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480" viewBox="0 0 640 480">'
        '<rect width="640" height="480" fill="#1a262f"/>'
        '<g fill="none" stroke="#4a6472" stroke-width="6" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="250" y="150" width="140" height="110" rx="12"/>'
        '<circle cx="290" cy="188" r="14"/>'
        '<path d="M258 246l44-40 32 28 22-18 26 30"/>'
        '</g>'
        '<text x="320" y="320" text-anchor="middle" font-family="Microsoft YaHei, Noto Sans SC, sans-serif" '
        'font-size="26" fill="#c8d6df">' + text + '</text>'
        '<text x="320" y="356" text-anchor="middle" font-family="Microsoft YaHei, Noto Sans SC, sans-serif" '
        'font-size="16" fill="#7c93a1">图片暂不可用</text>'
        '</svg>'
    )
    return svg.encode("utf-8")

# 本模块路由都是 async def，而 AmapService 连构造带调用都是同步阻塞的：
# MCPTool 初始化会 spawn `uvx amap-mcp-server` 并做服务发现
# （hello_agents/tools/builtin/protocol_tools.py:124 → :271），run() 也会
# 另开线程后 future.result() 等待（同文件 :447-458）。因此统一用
# asyncio.to_thread 派发，避免冻结事件循环导致进度推送与轮询一起失效。


class POIDetailResponse(BaseModel):
    """POI详情响应"""
    success: bool
    message: str
    data: Optional[dict] = None


@router.get(
    "/detail/{poi_id}",
    response_model=POIDetailResponse,
    summary="获取POI详情",
    description="根据POI ID获取详细信息,包括图片"
)
async def get_poi_detail(poi_id: str):
    """
    获取POI详情
    
    Args:
        poi_id: POI ID
        
    Returns:
        POI详情响应
    """
    try:
        amap_service = await asyncio.to_thread(get_amap_service)
        
        # 调用高德地图POI详情API
        result = await asyncio.to_thread(amap_service.get_poi_detail, poi_id)
        
        return POIDetailResponse(
            success=True,
            message="获取POI详情成功",
            data=result
        )
        
    except Exception as e:
        print(f"❌ 获取POI详情失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取POI详情失败: {str(e)}"
        )


@router.get(
    "/search",
    summary="搜索POI",
    description="根据关键词搜索POI"
)
async def search_poi(keywords: str, city: str = "北京"):
    """
    搜索POI

    Args:
        keywords: 搜索关键词
        city: 城市名称

    Returns:
        搜索结果
    """
    try:
        amap_service = await asyncio.to_thread(get_amap_service)
        result = await asyncio.to_thread(amap_service.search_poi, keywords, city)

        return {
            "success": True,
            "message": "搜索成功",
            "data": result
        }

    except Exception as e:
        print(f"❌ 搜索POI失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"搜索POI失败: {str(e)}"
        )


@router.get(
    "/image",
    summary="代理获取小红书图片",
    description="按景点名从缓存取图（miss 自动重搜新直链并立即下载），或代理白名单内的小红书稳定直链，规避 CDN 防盗链与时效签名（issue #28）"
)
async def proxy_attraction_image(
    name: Optional[str] = None,
    url: Optional[str] = None,
    keyword: Optional[str] = None,
    refresh: bool = False,
):
    """
    代理小红书图片，二选一传参：

    - name: 景点名。优先读关键词磁盘缓存；miss 时自动重搜新直链并立即下载
      （搜索返回的直链约 1 分钟即失效，浏览器直接引用必然 403）。
      refresh=true 时清掉该关键词缓存并强制重搜，供前端加载失败后重试。
    - keyword: 自定义搜索词（如「钟楼 夜景」），用于景点详解的多图场景。
      取不到图时返回 404，前端可隐藏该图而不是展示占位图。
    - url: 小红书稳定格式图片直链（仅限 *.xiaohongshu.com / *.xhscdn.com），
      用于代理行程数据中内嵌的直链。

    获取失败时返回 200 + 内联 SVG 占位图，避免浏览器出现破图图标。
    """
    from ...services.xhs_service import (
        XHSImageProxyError,
        fetch_xhs_image_bytes,
        get_photo_bytes_from_xhs,
    )

    if keyword:
        query = keyword.strip()[:100]
        if not query:
            raise HTTPException(status_code=400, detail="keyword 不能为空")
        result = await get_photo_bytes_from_xhs(query, refresh=refresh)
        if result is None:
            return Response(
                status_code=404,
                content=b"",
                media_type="image/jpeg",
                headers={"Cache-Control": "no-store"},
            )
        data, content_type = result
        return Response(
            content=data,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )

    if name:
        result = await get_photo_bytes_from_xhs(f"{name} 风景", refresh=refresh)
        if result is None:
            return Response(
                content=_placeholder_image_svg(name),
                media_type="image/svg+xml",
                headers={"Cache-Control": "no-store"},
            )
        data, content_type = result
        return Response(
            content=data,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )

    if url:
        try:
            # fetch_xhs_image_bytes 会读磁盘缓存并可能用 httpx 同步下载图片，
            # 必须派发到工作线程，避免阻塞事件循环（同 name 分支的做法）。
            data, content_type = await asyncio.to_thread(fetch_xhs_image_bytes, url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except (XHSImageProxyError, Exception) as e:
            print(f"❌ 图片代理失败: {e}")
            return Response(
                content=_placeholder_image_svg("景点图片"),
                media_type="image/svg+xml",
                headers={"Cache-Control": "no-store"},
            )
        return Response(
            content=data,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )

    raise HTTPException(status_code=400, detail="必须提供 name 或 url 查询参数")


@router.get(
    "/gallery",
    summary="获取景点实拍图库",
    description="优先返回高德 POI 实拍图（3 张，带城市消歧），用于详情页多图展示"
)
async def get_poi_gallery(name: str, city: Optional[str] = None, limit: int = 3):
    from ...services.poi_gallery import get_poi_photos

    photos = await get_poi_photos(name, city or "", limit=limit)
    return {
        "success": True,
        "message": "获取图库成功" if photos else "暂无图库",
        "data": {
            "name": name,
            "photos": photos,
            "source": "amap",
        },
    }


@router.get(
    "/photo",
    summary="获取景点图片",
    description="根据景点名称从小红书获取图片"
)
async def get_attraction_photo(name: str, city: Optional[str] = None):
    """
    获取景点图片

    Args:
        name: 景点名称
        city: 所在城市

    Returns:
        图片URL
    """
    try:
        from ...services.xhs_service import get_photo_from_xhs
        
        # 为了避免同名的流行歌曲（如许嵩的《断桥残雪》）、小说或人名干扰
        # 强制带上前缀“景点”，能够绝对限定搜索范围在旅游打卡贴内
        query_kw = f"{name} 风景"
        photo_url = await get_photo_from_xhs(query_kw)

        if not photo_url:
            # 兜底：交由前端展示默认占位图
            print(f"⚠️ 无法为 {name} 找到对应的小红书景点图片，返回空")
            photo_url = ""
            
        return {
            "success": True,
            "message": "获取图片成功",
            "data": {
                "name": name,
                "photo_url": photo_url
            }
        }

    except Exception as e:
        print(f"❌ 获取景点图片失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取景点图片失败: {str(e)}"
        )

