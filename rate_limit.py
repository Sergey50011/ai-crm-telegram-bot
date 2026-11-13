"""Простой in-memory rate limit по telegram user id."""

from __future__ import annotations

import time
from collections import defaultdict, deque


class UserRateLimiter:
    def __init__(self, max_per_minute: int) -> None:
        self._max = max(1, max_per_minute)
        self._window_sec = 60.0
        self._hits: dict[int, deque[float]] = defaultdict(deque)

    def allow(self, user_id: int) -> bool:
        now = time.monotonic()
        queue = self._hits[user_id]
        while queue and now - queue[0] > self._window_sec:
            queue.popleft()
        if len(queue) >= self._max:
            return False
        queue.append(now)
        return True
