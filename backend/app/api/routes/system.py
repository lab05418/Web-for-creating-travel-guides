"""系统能力与健康检查路由。

注意：不返回 API Key、Base URL 等敏感信息；健康检查只发一条极短探针。
"""

import asyncio
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ...config import get_settings
from ...services.llm_service import get_llm
from ...services.public_guard import client_ip, get_health_limiter

router = APIRouter(tags=["系统"])


@router.get("/runtime/capabilities")
async def runtime_capabilities():
    """前端据此决定设置页是否可写（不泄露任何密钥）。"""
    settings = get_settings()
    return {
        "success": True,
        "data": {
            "public_mode": settings.public_mode,
            "settings_writable": not settings.public_mode,
            "llm_provider": "openai-compatible",
            "llm_model": settings.openai_model,
        },
    }


@router.get("/llm/health")
async def llm_health(http_request: Request):
    """LLM 连通性探针：返回模型与延迟，不返回密钥或上游响应体。"""
    ip = client_ip(http_request)
    allowed, retry_after = await get_health_limiter().allow(ip)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"ok": False, "error": "rate_limited", "message": "健康检查过于频繁，请稍后再试"},
            headers={"Retry-After": str(retry_after)},
        )

    settings = get_settings()
    started = time.perf_counter()
    try:
        llm = get_llm()
        reply = await asyncio.to_thread(
            llm.invoke,
            [{"role": "user", "content": "ping"}],
            temperature=0,
            max_tokens=8,
            stream=False,
            timeout=30,
        )
        return {
            "ok": True,
            "model": getattr(llm, "model", settings.openai_model),
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "reply_chars": len(reply or ""),
        }
    except Exception as exc:  # noqa: BLE001 - 只暴露错误类型，避免泄露上游内容
        print(f"❌ LLM 健康检查失败: {type(exc).__name__}")
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "model": settings.openai_model,
                "error": type(exc).__name__,
                "message": "LLM 健康检查失败，请查看服务端日志",
            },
        )
