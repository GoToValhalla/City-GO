from __future__ import annotations

import time
from collections import OrderedDict, deque
from threading import Lock


class AbuseControlStore:
    def __init__(self, *, max_keys: int = 10_000) -> None:
        self._events: OrderedDict[str, deque[float]] = OrderedDict()
        self._max_keys = max_keys
        self._lock = Lock()

    def hit(self, key: str, *, limit: int, window_seconds: float) -> bool:
        now = time.monotonic()
        with self._lock:
            bucket = self._events.setdefault(key, deque())
            self._events.move_to_end(key)
            cutoff = now - window_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            while len(self._events) > self._max_keys:
                self._events.popitem(last=False)
            return True

    @property
    def key_count(self) -> int:
        with self._lock:
            return len(self._events)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
