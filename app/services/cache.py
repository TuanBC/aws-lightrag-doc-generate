"""Naive in-memory TTL cache for request throttling and memoization."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Generic, Optional, TypeVar


T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    value: T
    expires_at: float


class InMemoryTTLCache(Generic[T]):
    """Simple TTL cache suitable for single-process deployments."""

    def __init__(self, ttl_seconds: int = 120, max_items: int = 256) -> None:
        self.ttl = ttl_seconds
        self.max_items = max_items
        self._store: Dict[str, CacheEntry[T]] = {}

    def get(self, key: str) -> Optional[T]:
        entry = self._store.get(key)
        if not entry:
            return None
        if entry.expires_at < time.time():
            self._store.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: T) -> None:
        if len(self._store) >= self.max_items:
            # Drop the stalest entry
            oldest_key = min(self._store, key=lambda k: self._store[k].expires_at)
            self._store.pop(oldest_key, None)
        self._store[key] = CacheEntry(value=value, expires_at=time.time() + self.ttl)

    def clear(self) -> None:
        self._store.clear()
