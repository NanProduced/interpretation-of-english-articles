"""
TECD3 词典查询缓存。

多级缓存架构：
- L1: 进程内内存缓存（_L1_CACHE）- 极高频并发过滤
- L2: Redis 缓存 - 分布式缓存，跨实例共享
- L3: PostgreSQL - 最终源

故障降级：Redis 不可用时自动切换到 L1 + PostgreSQL 模式，不中断业务。
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from app.config.settings import get_settings

logger = logging.getLogger("app.cache")

# L1: 进程内缓存配置
_L1_CACHE: dict[str, tuple[dict[str, Any], float]] = {}  # query -> (data, expiry)
_L1_TTL_SECONDS = 60 * 60 * 24  # 24 hours
_L1_MAX_SIZE = 1000
_L1_LOCK = Lock()

# Redis 连接状态管理
@dataclass
class RedisState:
    client: Any = None
    initialized: bool = False
    last_failure_time: float = 0
    failure_backoff_seconds: int = 60
    lock: Lock = field(default_factory=Lock)


_REDIS_STATE = RedisState()


def _get_redis_client() -> Any:
    """
    获取 Redis 客户端（延迟初始化 + 故障降级）。
    
    返回 None 表示 Redis 不可用，调用方应降级到 L1 + PostgreSQL。
    """
    settings = get_settings()
    
    if not settings.redis_enabled:
        return None
    
    with _REDIS_STATE.lock:
        if _REDIS_STATE.client is not None and _REDIS_STATE.initialized:
            return _REDIS_STATE.client
        
        if time.time() - _REDIS_STATE.last_failure_time < _REDIS_STATE.failure_backoff_seconds:
            return None
        
        try:
            import redis.asyncio as redis
            _REDIS_STATE.client = redis.from_url(
                settings.redis_url,
                decode_responses=False,
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=False,
            )
            _REDIS_STATE.initialized = True
            logger.info("Redis cache initialized successfully")
            return _REDIS_STATE.client
        except Exception as e:
            _REDIS_STATE.last_failure_time = time.time()
            _REDIS_STATE.client = None
            _REDIS_STATE.initialized = False
            logger.warning("Redis connection failed, falling back to L1 cache only: %s", e)
            return None


def _l1_get(word: str) -> dict[str, Any] | None:
    """L1 进程内缓存查询"""
    entry = _L1_CACHE.get(word)
    if entry is None:
        return None
    data, expiry = entry
    if time.time() > expiry:
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


def _l2_get(word: str) -> dict[str, Any] | None:
    """L2 Redis 缓存查询（异步版本）"""
    return None


async def _l2_get_async(word: str) -> dict[str, Any] | None:
    """L2 Redis 缓存查询（异步版本）"""
    client = _get_redis_client()
    if client is None:
        return None
    
    try:
        import orjson
        data_bytes = await client.get(f"dict:{word}")
        if data_bytes is None:
            return None
        data = orjson.loads(data_bytes)
        logger.debug("L2 Redis cache hit: %s", word)
        return data
    except Exception as e:
        _REDIS_STATE.last_failure_time = time.time()
        logger.warning("Redis GET failed, marking as unavailable: %s", e)
        return None


def _l2_set(word: str, data: dict[str, Any]) -> None:
    """L2 Redis 缓存写入（异步版本）"""
    pass


async def _l2_set_async(word: str, data: dict[str, Any]) -> None:
    """L2 Redis 缓存写入（异步版本）"""
    client = _get_redis_client()
    if client is None:
        return
    
    try:
        import orjson
        data_bytes = orjson.dumps(data)
        settings = get_settings()
        ttl = getattr(settings, "redis_cache_ttl", _L1_TTL_SECONDS)
        await client.setex(f"dict:{word}", ttl, data_bytes)
        logger.debug("L2 Redis cache set: %s", word)
    except Exception as e:
        _REDIS_STATE.last_failure_time = time.time()
        logger.warning("Redis SET failed, marking as unavailable: %s", e)


def get(word: str) -> dict[str, Any] | None:
    """
    同步缓存查询（L1 优先）。
    
    注意：此方法不查询 Redis L2 缓存。使用 get_async 获取完整的多级缓存能力。
    """
    return _l1_get(word)


async def get_async(word: str) -> dict[str, Any] | None:
    """
    异步多级缓存查询。
    
    缓存层级：L1 → L2 → (miss)
    
    返回 None 表示缓存未命中，需要查询 PostgreSQL。
    """
    l1_result = _l1_get(word)
    if l1_result is not None:
        logger.debug("L1 cache hit: %s", word)
        return l1_result
    
    l2_result = await _l2_get_async(word)
    if l2_result is not None:
        _l1_set(word, l2_result)
        return l2_result
    
    logger.debug("Cache miss: %s", word)
    return None


def set(word: str, data: dict[str, Any]) -> None:
    """
    同步缓存写入（仅 L1）。
    
    注意：此方法仅写入 L1 缓存。使用 set_async 获取完整的多级缓存能力。
    """
    _l1_set(word, data)


async def set_async(word: str, data: dict[str, Any]) -> None:
    """
    异步多级缓存写入。
    
    同时写入 L1 和 L2 缓存。L2 写入失败不影响 L1 写入，
    确保核心业务不受 Redis 故障影响。
    """
    _l1_set(word, data)
    await _l2_set_async(word, data)


def clear_l1() -> None:
    """清空 L1 进程内缓存（用于测试或调试）"""
    with _L1_LOCK:
        _L1_CACHE.clear()
    logger.info("L1 cache cleared")


async def clear_l2() -> None:
    """清空 L2 Redis 缓存（用于测试或调试）"""
    client = _get_redis_client()
    if client is None:
        return
    try:
        keys = await client.keys("dict:*")
        if keys:
            await client.delete(*keys)
        logger.info("L2 cache cleared, %d keys deleted", len(keys))
    except Exception as e:
        logger.warning("Redis clear failed: %s", e)


def get_cache_stats() -> dict[str, Any]:
    """获取缓存统计信息（用于监控和调试）"""
    settings = get_settings()
    with _L1_LOCK:
        l1_size = len(_L1_CACHE)
    
    return {
        "l1": {
            "size": l1_size,
            "max_size": _L1_MAX_SIZE,
            "ttl_seconds": _L1_TTL_SECONDS,
        },
        "l2": {
            "enabled": settings.redis_enabled,
            "connected": _REDIS_STATE.client is not None and _REDIS_STATE.initialized,
            "last_failure_time": _REDIS_STATE.last_failure_time,
            "failure_backoff_seconds": _REDIS_STATE.failure_backoff_seconds,
        },
    }
