"""公开发布防护：客户端 IP 识别、按 IP 限流、全局并发闸门。

说明：
- 全部为进程内实现，适合单实例部署；多实例需换成 Redis 等共享存储。
- 不依赖 GPU、不依赖任何外部服务。
"""

from __future__ import annotations

import asyncio
import hmac
import math
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional, Tuple

from fastapi import Request

from ..config import get_settings

_DAY_SECONDS = 24 * 3600
_MINUTE_SECONDS = 60
_MAX_TRACKED_IPS = 10000


def client_ip(request: Request) -> str:
    """解析真实客户端 IP；仅在显式信任反向代理时读取转发头。"""
    settings = get_settings()
    if settings.trust_proxy:
        forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        if forwarded:
            return forwarded
        real_ip = (request.headers.get("x-real-ip") or "").strip()
        if real_ip:
            return real_ip
    return request.client.host if request.client else "unknown"


class SlidingWindowLimiter:
    """按 key（IP）的滑动窗口限流：日上限 + 分钟突发上限。"""

    def __init__(self, per_day: int, per_minute: int) -> None:
        self.per_day = max(0, per_day)
        self.per_minute = max(0, per_minute)
        self._events: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def allow(self, key: str) -> Tuple[bool, int]:
        """返回 (是否放行, 建议 Retry-After 秒数)。"""
        now = time.monotonic()
        async with self._lock:
            queue = self._events[key]

            # 清理超过 24h 的记录
            while queue and now - queue[0] >= _DAY_SECONDS:
                queue.popleft()

            if self.per_day and len(queue) >= self.per_day:
                retry = max(1, math.ceil(_DAY_SECONDS - (now - queue[0])))
                return False, retry

            if self.per_minute:
                recent = [ts for ts in queue if now - ts < _MINUTE_SECONDS]
                if len(recent) >= self.per_minute:
                    retry = max(1, math.ceil(_MINUTE_SECONDS - (now - recent[0])))
                    return False, retry

            queue.append(now)
            if len(self._events) > _MAX_TRACKED_IPS:
                # 简单清理：丢弃最久未活跃的 10%
                stale = sorted(self._events.items(), key=lambda item: item[1][-1] if item[1] else 0)
                for old_key, _ in stale[: max(1, len(stale) // 10)]:
                    self._events.pop(old_key, None)
            return True, 0

    def reset(self) -> None:
        self._events.clear()


class PlanGate:
    """规划任务的全局并发闸门：限制同时执行数，并限制排队长度。"""

    def __init__(self, max_concurrent: int, queue_limit: int) -> None:
        self.max_concurrent = max(1, max_concurrent)
        self.queue_limit = max(0, queue_limit)
        self._sem = asyncio.Semaphore(self.max_concurrent)
        self._waiting = 0
        self._lock = asyncio.Lock()

    async def admit(self) -> bool:
        """提交前占位；排队已满返回 False。"""
        async with self._lock:
            if self._waiting >= self.queue_limit:
                return False
            self._waiting += 1
            return True

    async def run(self, coro):
        """在并发闸门内执行协程，并维护排队计数。"""
        try:
            await self._sem.acquire()
        except BaseException:
            async with self._lock:
                self._waiting = max(0, self._waiting - 1)
            raise

        async with self._lock:
            self._waiting = max(0, self._waiting - 1)

        try:
            return await coro
        finally:
            self._sem.release()

    @property
    def waiting(self) -> int:
        return self._waiting


_plan_limiter: Optional[SlidingWindowLimiter] = None
_plan_gate: Optional[PlanGate] = None
_health_limiter: Optional[SlidingWindowLimiter] = None


def get_plan_limiter() -> SlidingWindowLimiter:
    global _plan_limiter
    if _plan_limiter is None:
        settings = get_settings()
        _plan_limiter = SlidingWindowLimiter(
            per_day=settings.plan_rate_limit_per_day,
            per_minute=settings.plan_burst,
        )
    return _plan_limiter


def get_plan_gate() -> PlanGate:
    global _plan_gate
    if _plan_gate is None:
        settings = get_settings()
        _plan_gate = PlanGate(
            max_concurrent=settings.max_concurrent_plans,
            queue_limit=settings.plan_queue_limit,
        )
    return _plan_gate


def get_health_limiter() -> SlidingWindowLimiter:
    global _health_limiter
    if _health_limiter is None:
        _health_limiter = SlidingWindowLimiter(per_day=0, per_minute=1)
    return _health_limiter


def reset_guards() -> None:
    """重置单例（测试或运行时配置变更后使用）。"""
    global _plan_limiter, _plan_gate, _health_limiter
    _plan_limiter = None
    _plan_gate = None
    _health_limiter = None


def is_admin_token(token: Optional[str]) -> bool:
    """管理员令牌校验（常时比较，避免时序侧信道）。"""
    settings = get_settings()
    if not settings.admin_token or not token:
        return False
    return hmac.compare_digest(token, settings.admin_token)
