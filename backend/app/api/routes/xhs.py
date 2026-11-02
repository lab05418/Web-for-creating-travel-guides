"""小红书会话与运行状态 API。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from ...config import get_settings as get_app_settings
from ...services.public_guard import is_admin_token
from ...services.xhs.metrics import metrics
from ...services.xhs.session_manager import get_session_manager
from ...services.xhs_service import get_xhs_client

router = APIRouter(prefix="/xhs", tags=["小红书会话"])


class XhsCookiePayload(BaseModel):
    cookie: str = Field(..., min_length=1, max_length=50000, description="浏览器 Cookie 字符串或 JSON")
    account_label: str = Field(default="default", max_length=80)
    user_agent: str = Field(default="", max_length=500)


def _require_admin(token: Optional[str]) -> None:
    if get_app_settings().public_mode and not is_admin_token(token):
        raise HTTPException(status_code=403, detail="公共模式：修改小红书会话需要管理员令牌")


@router.get("/status", summary="小红书会话与指标状态")
async def xhs_status() -> Dict[str, Any]:
    manager = get_session_manager()
    return {
        "success": True,
        "data": {
            "session": manager.status(),
            "metrics": metrics.snapshot(),
        },
    }


@router.post("/session", summary="导入/更新小红书 Cookie")
async def import_xhs_cookie(
    payload: XhsCookiePayload,
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> Dict[str, Any]:
    _require_admin(x_admin_token)
    try:
        manager = get_session_manager()
        record = manager.import_cookie(
            payload.cookie,
            account_label=payload.account_label,
            user_agent=payload.user_agent,
        )
        return {
            "success": True,
            "message": "小红书 Cookie 已加密保存",
            "data": {**manager.status(), "imported_id": record.get("id")},
        }
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/session/probe", summary="探测小红书会话是否可用")
async def probe_xhs_session(
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> Dict[str, Any]:
    _require_admin(x_admin_token)
    try:
        client = get_xhs_client()
        result = client.search_notes("旅行", page_size=1)
        return {
            "success": True,
            "message": "会话可用",
            "data": {
                "session": get_session_manager().status(),
                "items": len(result.get("data", {}).get("items", [])),
            },
        }
    except Exception as error:
        return {
            "success": False,
            "message": str(error),
            "data": {"session": get_session_manager().status()},
        }


@router.post("/session/disable", summary="停用当前小红书会话")
async def disable_xhs_session(
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> Dict[str, Any]:
    _require_admin(x_admin_token)
    get_session_manager().disable()
    return {"success": True, "data": get_session_manager().status()}
