"""轻量登录限流；网关限流的应用内第二道防线。"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from .config import settings

_lock = threading.Lock()
_failures: dict[str, deque[float]] = defaultdict(deque)
_blocked_until: dict[str, float] = {}
_actions: dict[str, deque[float]] = defaultdict(deque)


def _prune(key: str, now: float) -> None:
    failures = _failures[key]
    cutoff = now - max(1, settings.login_rate_window_seconds)
    while failures and failures[0] < cutoff:
        failures.popleft()
    if not failures:
        _failures.pop(key, None)


def retry_after(key: str) -> int:
    now = time.monotonic()
    with _lock:
        blocked = _blocked_until.get(key, 0)
        if blocked > now:
            return max(1, int(blocked - now) + 1)
        _blocked_until.pop(key, None)
        _prune(key, now)
        return 0


def record_failure(key: str) -> int:
    now = time.monotonic()
    with _lock:
        _prune(key, now)
        failures = _failures[key]
        failures.append(now)
        if len(failures) >= max(1, settings.login_rate_limit):
            until = now + max(1, settings.login_block_seconds)
            _blocked_until[key] = until
            failures.clear()
            return max(1, settings.login_block_seconds)
        return 0


def record_success(key: str) -> None:
    with _lock:
        _failures.pop(key, None)
        _blocked_until.pop(key, None)


def check_action(key: str, *, limit: int, window_seconds: int) -> int:
    """原子滑动窗口限流；命中时返回 Retry-After 秒数。"""
    now = time.monotonic()
    window = max(1, window_seconds)
    with _lock:
        events = _actions[key]
        cutoff = now - window
        while events and events[0] <= cutoff:
            events.popleft()
        if len(events) >= max(1, limit):
            return max(1, int(events[0] + window - now) + 1)
        events.append(now)
        return 0


def reset() -> None:
    """仅用于测试和进程级管理。"""
    with _lock:
        _failures.clear()
        _blocked_until.clear()
        _actions.clear()
