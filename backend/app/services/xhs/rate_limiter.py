"""小红书请求限流与单 worker 调度。"""

from __future__ import annotations

import os
import random
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, TypeVar

from .errors import XhsAuthError, XhsNetworkError, XhsParseError, XhsRateLimitError, XhsSignatureError

T = TypeVar("T")


class RateGate:
    """线程安全的固定间隔令牌门，默认 1 次 / 4 秒。"""

    def __init__(self, interval_seconds: float):
        self.interval = max(0.5, float(interval_seconds or 4))
        self._lock = threading.Lock()
        self._next_at = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait_for = max(0.0, self._next_at - now)
            self._next_at = max(now, self._next_at) + self.interval
        if wait_for > 0:
            time.sleep(wait_for)


class XhsRequestScheduler:
    """单 worker + 限流 + 有限重试。

    只允许一个请求在途，避免并发触发平台风控；网络/限流失败退避重试，
    鉴权/签名/解析失败不重试。
    """

    def __init__(self, interval_seconds: float | None = None):
        if interval_seconds is None:
            try:
                interval_seconds = float(os.getenv("XHS_REQUEST_INTERVAL", "4"))
            except ValueError:
                interval_seconds = 4.0
        self.gate = RateGate(interval_seconds)
        try:
            self.default_retries = max(0, int(os.getenv("XHS_REQUEST_RETRIES", "2")))
        except ValueError:
            self.default_retries = 2
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="xhs-request")
        self._lock = threading.Lock()

    def run(self, fn: Callable[..., T], *args: Any, retries: int | None = None, **kwargs: Any) -> T:
        attempts = self.default_retries if retries is None else retries
        future: Future[T] = self._executor.submit(self._run_with_retry, fn, args, kwargs, attempts)
        return future.result()

    def _run_with_retry(
        self,
        fn: Callable[..., T],
        args: tuple,
        kwargs: dict,
        retries: int,
    ) -> T:
        attempt = 0
        while True:
            self.gate.wait()
            try:
                return fn(*args, **kwargs)
            except (XhsAuthError, XhsSignatureError, XhsParseError):
                raise
            except (XhsRateLimitError, XhsNetworkError):
                if attempt >= max(0, retries):
                    raise
                attempt += 1
                # 指数退避 + 抖动，避免同步重试风暴
                time.sleep(min(30.0, (2 ** attempt) + random.uniform(0.3, 1.2)))

    def shutdown(self) -> None:
        with self._lock:
            self._executor.shutdown(wait=False, cancel_futures=True)


_SCHEDULER: XhsRequestScheduler | None = None
_SCHEDULER_LOCK = threading.Lock()


def get_scheduler() -> XhsRequestScheduler:
    global _SCHEDULER
    if _SCHEDULER is None:
        with _SCHEDULER_LOCK:
            if _SCHEDULER is None:
                _SCHEDULER = XhsRequestScheduler()
    return _SCHEDULER
