"""运行时配置 API 路由"""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from ...config import get_runtime_settings, get_settings as get_app_settings, update_runtime_settings
from ...services.amap_service import reset_amap_service
from ...services.llm_service import reset_llm
from ...services.public_guard import is_admin_token
from ...services.xhs.session_manager import get_session_manager
from ...agents.trip_planner_agent import reset_trip_planner_agent

router = APIRouter(prefix="/settings", tags=["运行时配置"])


class RuntimeSettingsPayload(BaseModel):
    """前端设置页提交的运行时配置。"""

    vite_amap_web_key: Optional[str] = Field(default=None, description="高德 Web 服务 Key")
    vite_amap_web_js_key: Optional[str] = Field(default=None, description="高德 JS SDK Key")
    vite_amap_security_js_code: Optional[str] = Field(default=None, description="高德 JS API 安全密钥")
    xhs_cookie: Optional[str] = Field(default=None, description="小红书 Cookie")
    openai_api_key: Optional[str] = Field(default=None, description="LLM API Key")
    openai_base_url: Optional[str] = Field(default=None, description="LLM Base URL")
    openai_model: Optional[str] = Field(default=None, description="LLM 模型")


@router.get("")
async def get_settings():
    """获取当前运行时配置。"""
    data = get_runtime_settings()
    session = get_session_manager().status()
    # 不再回传真实 Cookie；前端只显示加密保存状态。
    data["xhs_cookie"] = "••••••••" if session.get("configured") else ""
    data["xhs_session"] = session
    return {
        "success": True,
        "message": "ok",
        "data": data,
    }


@router.put("")
async def save_settings(
    payload: RuntimeSettingsPayload,
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    """保存运行时配置并立即生效。

    公共模式（PUBLIC_MODE=true）下必须携带正确的 X-Admin-Token，
    避免任意访客修改后端模型 Key 或地图 Key。
    """
    if get_app_settings().public_mode and not is_admin_token(x_admin_token):
        raise HTTPException(status_code=403, detail="公共模式：修改配置需要管理员令牌")
    try:
        updates = payload.model_dump(exclude_unset=True)
        cookie_value = updates.pop("xhs_cookie", None)
        if isinstance(cookie_value, str) and cookie_value.strip() and "•" not in cookie_value:
            get_session_manager().import_cookie(cookie_value, account_label="settings")
        updated = update_runtime_settings(updates)
        # Cookie 只保存在加密会话表，不再写入 runtime_settings.json。
        updated["xhs_cookie"] = "••••••••" if get_session_manager().status().get("configured") else ""
        updated["xhs_session"] = get_session_manager().status()

        # 重置单例，确保新配置立即生效
        reset_llm()
        reset_amap_service()
        reset_trip_planner_agent()

        return {
            "success": True,
            "message": "配置已保存并立即生效",
            "data": updated,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置失败: {str(e)}") from e
