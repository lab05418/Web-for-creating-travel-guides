"""地点管理 API：列表、新增、修改、删除、排序、设置酒店。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...models.schemas import PlaceCreate, PlaceUpdate
from ...services import place_store
from ...services.place_price import lookup_place_price
from .trip import _get_task, _persist_task_state

router = APIRouter(prefix="/plans", tags=["地点管理"])


def _get_plan_task(plan_id: str) -> Dict[str, Any]:
    task = _get_task(plan_id)
    if not task:
        raise HTTPException(status_code=404, detail="行程不存在")
    if task.get("status") != "completed":
        raise HTTPException(status_code=409, detail="行程尚未完成，暂不能管理地点")

    # 内存中的新任务保存的是 TripPlanResponse（Pydantic 对象），
    # 从磁盘恢复的任务才是 dict；地点接口统一按 dict 读取。
    result = task.get("result")
    if hasattr(result, "model_dump"):
        result = result.model_dump(mode="json")
    if not isinstance(result, dict):
        result = {}
    task["result"] = result

    if not result.get("data"):
        raise HTTPException(status_code=404, detail="行程数据不存在")
    if place_store.seed_from_plan(plan_id, task):
        _persist_task_state(plan_id, task)
    return task


def _ok(data: Any) -> Dict[str, Any]:
    return {"success": True, "message": "", "data": data}


@router.get("/{plan_id}/places", summary="地点列表")
def get_places(plan_id: str, day_index: Optional[int] = None, type: Optional[str] = None):
    _get_plan_task(plan_id)
    places = place_store.list_places(plan_id)
    if day_index is not None:
        places = [item for item in places if item.get("day_index") == day_index]
    if type:
        places = [item for item in places if item.get("type") == type]
    return _ok(places)


def _city_for_day(plan: Dict[str, Any], day_index: Optional[int]) -> str:
    days = plan.get("days") or []
    if day_index is not None and 0 <= day_index < len(days):
        day_city = str((days[day_index] or {}).get("city") or "").strip()
        if day_city:
            return day_city
    return str(plan.get("city") or "").strip()


def _effective_type(requested: str, inferred: str) -> str:
    """用户选 custom/景点但内容明显是餐饮/住宿/车站时，自动纠正类型。"""
    if inferred in {"hotel", "restaurant", "station"} and requested in {"custom", "attraction"}:
        return inferred
    if requested == "custom" and inferred in {"hotel", "attraction", "restaurant", "station"}:
        return inferred
    return requested


@router.post("/{plan_id}/places", summary="新增地点", status_code=201)
async def create_place(plan_id: str, payload: PlaceCreate):
    task = _get_plan_task(plan_id)
    plan = place_store._plan_data(task)
    requested_type = payload.type
    city = _city_for_day(plan, payload.day_index)

    # 实时查询失败/无价格不阻断添加，只是 price=None 且不进入预算。
    price_info = await lookup_place_price(
        name=payload.name,
        city=city,
        address=payload.address,
        note=payload.note or "",
        place_type=requested_type,
        poi_id=payload.amap_poi_id or "",
    )
    effective_type = _effective_type(requested_type, str(price_info.get("inferred_type") or "custom"))
    if effective_type == "hotel" and payload.day_index is None:
        effective_type = requested_type
    data = payload.model_dump()
    data["type"] = effective_type
    data["price"] = price_info.get("price")
    data["price_source"] = price_info.get("price_source") or ""
    data["inferred_type"] = price_info.get("inferred_type") or effective_type

    try:
        place = place_store.create_place(plan_id, data, task)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _persist_task_state(plan_id, task)

    place.update(
        {
            "requested_type": requested_type,
            "inferred_type": price_info.get("inferred_type") or effective_type,
            "price": price_info.get("price"),
            "price_source": price_info.get("price_source") or "unavailable",
            "price_kind": price_info.get("price_kind") or "unknown",
            "price_available": bool(price_info.get("has_price")),
            "itinerary_adjusted": bool(place.get("itinerary_adjusted")) or effective_type != requested_type,
        }
    )
    return _ok(place)


@router.patch("/{plan_id}/places/{place_id}", summary="修改地点")
def update_place(plan_id: str, place_id: str, payload: PlaceUpdate):
    task = _get_plan_task(plan_id)
    data = payload.model_dump(exclude_unset=True)
    try:
        place = place_store.update_place(plan_id, place_id, data, task)
    except place_store.ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not place:
        raise HTTPException(status_code=404, detail="地点不存在")
    _persist_task_state(plan_id, task)
    return _ok(place)


@router.delete("/{plan_id}/places/{place_id}", summary="删除地点", status_code=204)
def delete_place(plan_id: str, place_id: str):
    task = _get_plan_task(plan_id)
    if not place_store.delete_place(plan_id, place_id, task):
        raise HTTPException(status_code=404, detail="地点不存在")
    _persist_task_state(plan_id, task)
    return None


class ReorderPayload(BaseModel):
    day_index: int = Field(ge=0)
    ids: List[str] = Field(default_factory=list)


@router.put("/{plan_id}/places/order", summary="地点排序")
def reorder_places(plan_id: str, payload: ReorderPayload):
    task = _get_plan_task(plan_id)
    try:
        place_store.reorder_places(plan_id, payload.day_index, payload.ids, task)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _persist_task_state(plan_id, task)
    return _ok(place_store.list_places(plan_id))


class HotelPayload(BaseModel):
    place_id: str


@router.put("/{plan_id}/days/{day_index}/hotel", summary="设置当日酒店")
def set_hotel(plan_id: str, day_index: int, payload: HotelPayload):
    task = _get_plan_task(plan_id)
    try:
        place = place_store.set_hotel(plan_id, day_index, payload.place_id, task)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _persist_task_state(plan_id, task)
    return _ok(place)
