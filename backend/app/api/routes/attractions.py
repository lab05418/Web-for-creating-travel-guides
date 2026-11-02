"""景点深度导览 API。

行程概览卡片点击「进入」后，前端在当前位置请求该接口，
展示景点的历史背景、有趣细节与实用提示，不再跳转到每日行程。
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...services.attraction_guide import get_attraction_guide
from ...services.popular_attractions import get_popular_attractions

router = APIRouter(prefix="/attractions", tags=["景点导览"])


class AttractionGuideRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80, description="景点名称")
    city: str = Field(default="", max_length=60, description="所在城市")
    address: str = Field(default="", max_length=200, description="景点地址")
    description: str = Field(default="", max_length=2000, description="行程中的景点简介")
    category: str = Field(default="", max_length=40, description="景点类别")


@router.post("/guide", summary="获取景点深度导览")
async def attraction_guide(payload: AttractionGuideRequest) -> Dict[str, Any]:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="景点名称不能为空")

    guide = await get_attraction_guide(
        name=name,
        city=payload.city.strip(),
        address=payload.address.strip(),
        description=payload.description.strip(),
        category=payload.category.strip(),
    )
    return {"success": True, "message": "", "data": guide}


@router.get("/popular", summary="获取当前行程之外的热门景点")
async def popular_attractions(
    city: str = Query(..., min_length=1, max_length=60, description="城市"),
    exclude: str = Query(default="", max_length=3000, description="逗号分隔的已在行程中的景点名"),
    limit: int = Query(default=12, ge=1, le=24, description="返回数量"),
) -> Dict[str, Any]:
    exclude_names = [
        name.strip()
        for name in str(exclude or "").split(",")
        if name.strip()
    ]
    items = await get_popular_attractions(
        city=city.strip(),
        exclude_names=exclude_names,
        limit=limit,
    )
    return {
        "success": True,
        "message": "",
        "data": {
            "city": city.strip(),
            "items": items,
        },
    }
