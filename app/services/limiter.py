"""Very small fixed-window rate limiter for in-process deployments."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class RateLimitWindow:
    count: int
    window_start: float


class RateLimiter:
    """Fixed-window rate limiter keyed by arbitrary identifiers (e.g., IP address)."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._windows: dict[str, RateLimitWindow] = defaultdict(
            lambda: RateLimitWindow(count=0, window_start=time.time())
        )

    def allow(self, key: str) -> bool:
        now = time.time()
        window = self._windows[key]
        if now - window.window_start > self.window_seconds:
            window.window_start = now
            window.count = 0
        if window.count >= self.max_requests:
            return False
        window.count += 1
        return True
