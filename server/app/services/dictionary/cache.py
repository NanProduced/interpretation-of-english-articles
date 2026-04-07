"""
ECDICT 词典查询缓存。

仅使用 L1 进程内内存缓存。
L2 磁盘 JSON 缓存已废弃（见 production-architecture-and-deployment-plan.md）；
正式真源为 PostgreSQL，Redis 为第二阶段可选增强。
"""

from __future__ import annotations

import time
from threading import Lock
from typing import Any

# L1: 进程内缓存配置
_L1_CACHE: dict[str, tuple[dict[str, Any], float]] = {}  # word -> (data, expiry)
_L1_TTL_SECONDS = 60 * 60  # 1 hour
_L1_MAX_SIZE = 1000
_L1_LOCK = Lock()


def _l1_get(word: str) -> dict[str, Any] | None:
    """L1 进程内缓存查询"""
    entry = _L1_CACHE.get(word)
    if entry is None:
        return None
    data, expiry = entry
    if time.time() > expiry:
        # 已过期，删除
        _L1_CACHE.pop(word, None)
        return None
    return data


def _l1_set(word: str, data: dict[str, Any]) -> None:
    """写入 L1 进程内缓存"""
    with _L1_LOCK:
        if len(_L1_CACHE) >= _L1_MAX_SIZE:
            expired = [k for k, (_, exp) in _L1_CACHE.items() if time.time() > exp]
            for k in expired[: _L1_MAX_SIZE // 2]:
                _L1_CACHE.pop(k, None)

        _L1_CACHE[word] = (data, time.time() + _L1_TTL_SECONDS)


def get(word: str) -> dict[str, Any] | None:
    """L1 进程内缓存查询"""
    return _l1_get(word)


def set(word: str, data: dict[str, Any]) -> None:
    """写入 L1 缓存"""
    _l1_set(word, data)
