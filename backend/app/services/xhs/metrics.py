"""小红书抓取指标（进程内，轻量可观测）。"""

from __future__ import annotations

import threading
from collections import Counter
from typing import Any, Dict


class XhsMetrics:
    def __init__(self):
        self._lock = threading.Lock()
        self._counters: Counter = Counter()
        self._latency_ms: list[float] = []

    def inc(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[name] += amount

    def observe_latency(self, ms: float) -> None:
        with self._lock:
            self._latency_ms.append(float(ms))
            if len(self._latency_ms) > 500:
                self._latency_ms = self._latency_ms[-500:]

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            latencies = sorted(self._latency_ms)
            p95 = None
            if latencies:
                index = min(len(latencies) - 1, int(len(latencies) * 0.95))
                p95 = round(latencies[index], 1)
            return {
                "counters": dict(self._counters),
                "latency_ms_p95": p95,
                "latency_samples": len(latencies),
            }


metrics = XhsMetrics()
