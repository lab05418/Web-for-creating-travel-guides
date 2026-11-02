"""进程内 TTL 缓存，用于搜索结果与详情。

单实例部署足够；多实例时可替换为 Redis，接口不变。
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional, Tuple


class TTLCache:
    def __init__(self, maxsize: int = 512):
        self.maxsize = maxsize
        self._lock = threading.Lock()
        self._data: Dict[str, Tuple[float, Any]] = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str, allow_stale: bool = False) -> Optional[Any]:
        now = time.time()
        with self._lock:
            item = self._data.get(key)
            if not item:
                self.misses += 1
                return None
            expires_at, value = item
            if expires_at < now and not allow_stale:
                self.misses += 1
                return None
            self.hits += 1
            return value

    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        with self._lock:
            self._data[key] = (time.time() + max(1.0, ttl_seconds), value)
            if len(self._data) > self.maxsize:
                oldest = min(self._data, key=lambda k: self._data[k][0])
                self._data.pop(oldest, None)

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {"size": len(self._data), "hits": self.hits, "misses": self.misses}
