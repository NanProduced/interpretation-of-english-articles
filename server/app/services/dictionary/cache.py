from __future__ import annotations

import json
import os
import time
from pathlib import Path
from threading import Lock
from typing import Any

# L1: 进程内缓存配置
_L1_CACHE: dict[str, tuple[dict[str, Any], float]] = {}  # word -> (data, expiry)
_L1_TTL_SECONDS = 60 * 60  # 1 hour
_L1_MAX_SIZE = 1000
_L1_LOCK = Lock()

# L2: 文件缓存目录
_CACHE_DIR = Path(".cache/dictionary")
_L2_LOCK = Lock()


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
    # 容量超限时清理过期条目
    if len(_L1_CACHE) >= _L1_MAX_SIZE:
        expired = [k for k, (_, exp) in _L1_CACHE.items() if time.time() > exp]
        for k in expired[: _L1_MAX_SIZE // 2]:
            _L1_CACHE.pop(k, None)

    _L1_CACHE[word] = (data, time.time() + _L1_TTL_SECONDS)


def _l2_get(word: str) -> dict[str, Any] | None:
    """L2 文件缓存查询"""
    path = _CACHE_DIR / f"{word.lower().replace('/', '_')}.json"
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _l2_set(word: str, data: dict[str, Any]) -> None:
    """写入 L2 文件缓存"""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _CACHE_DIR / f"{word.lower().replace('/', '_')}.json"
    with _L2_LOCK:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except OSError:
            pass  # 缓存写入失败不影响主流程


def get(word: str) -> dict[str, Any] | None:
    """两级缓存查询: L1 → L2"""
    # L1
    data = _l1_get(word)
    if data is not None:
        return data
    # L2
    data = _l2_get(word)
    if data is not None:
        # 回填 L1
        _l1_set(word, data)
        return data
    return None


def set(word: str, data: dict[str, Any]) -> None:
    """写入 L1 + L2"""
    _l1_set(word, data)
    _l2_set(word, data)
