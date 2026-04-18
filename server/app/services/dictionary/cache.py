"""
TECD3 词典查询缓存。

多级缓存架构：
- L1: 进程内内存缓存（_L1_CACHE）- 极高频并发过滤
- L2: Redis 缓存 - 分布式缓存，跨实例共享（使用项目全局 RedisPool）
- L3: PostgreSQL - 最终源

故障降级：Redis 不可用时自动切换到 L1 + PostgreSQL 模式，不中断业务。
运行时故障保护：Redis 操作失败后 60 秒内不再尝试，避免每次请求都等待超时。
"""

from __future__ import annotations

import logging
import time
from threading import Lock
from typing import Any

from app.config.settings import get_settings
from app.database.connection import get_redis

logger = logging.getLogger("app.cache")

# L1: 进程内缓存配置
_L1_CACHE: dict[str, tuple[dict[str, Any], float]] = {}  # query -> (data, expiry)
_L1_TTL_SECONDS = 60 * 60 * 24  # 24 hours
_L1_MAX_SIZE = 1000
_L1_LOCK = Lock()

# Redis 故障回退状态管理（不管理连接，只管理故障回退）
_L2_FAILURE_LOCK = Lock()
_L2_LAST_FAILURE_TIME: float = 0
_L2_FAILURE_BACKOFF_SECONDS: int = 60


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
            
            if expired:
                to_remove = expired[: _L1_MAX_SIZE // 2]
            else:
                to_remove = list(_L1_CACHE.keys())[: _L1_MAX_SIZE // 2]
            
            for k in to_remove:
                _L1_CACHE.pop(k, None)

        _L1_CACHE[word] = (data, time.time() + _L1_TTL_SECONDS)


def _l2_should_skip() -> bool:
    """检查是否应该跳过 Redis 操作（故障回退期间）"""
    with _L2_FAILURE_LOCK:
        return time.time() - _L2_LAST_FAILURE_TIME < _L2_FAILURE_BACKOFF_SECONDS


def _l2_mark_failed() -> None:
    """标记 Redis 操作失败，进入故障回退期"""
    global _L2_LAST_FAILURE_TIME
    with _L2_FAILURE_LOCK:
        _L2_LAST_FAILURE_TIME = time.time()
    logger.warning(
        "Redis operation failed, entering backoff period (%ds)",
        _L2_FAILURE_BACKOFF_SECONDS,
    )


def _l2_mark_recovered() -> None:
    """标记 Redis 恢复正常"""
    global _L2_LAST_FAILURE_TIME
    with _L2_FAILURE_LOCK:
        if _L2_LAST_FAILURE_TIME > 0:
            _L2_LAST_FAILURE_TIME = 0
            logger.info("Redis operation succeeded, backoff period ended")


async def _l2_get_client() -> Any:
    """
    获取 Redis 客户端（使用项目全局连接池）。
    
    自动恢复机制：
    - 如果 RedisPool 为 None 但 redis_enabled = True，尝试重新初始化连接
    - 如果重新初始化失败，进入故障回退期（60秒内不再尝试）
    
    返回 None 表示：
    1. Redis 未启用（redis_enabled=False）
    2. Redis 连接池未初始化且重新初始化失败
    3. 处于故障回退期（最近操作失败，暂时不再尝试）
    """
    from app.database.connection import init_redis
    
    settings = get_settings()
    
    if not settings.redis_enabled:
        return None
    
    if _l2_should_skip():
        return None
    
    client = await get_redis()
    
    if client is None:
        logger.info("RedisPool is None, attempting to reinitialize...")
        try:
            client = await init_redis(settings.redis_url, enabled=True)
            if client is not None:
                logger.info("Redis reinitialized successfully")
                _l2_mark_recovered()
        except Exception as e:
            _l2_mark_failed()
            logger.warning("Redis reinitialization failed: %s", e)
            return None
    
    return client


async def _l2_get_async(word: str) -> dict[str, Any] | None:
    """L2 Redis 缓存查询（使用项目全局连接池）"""
    client = await _l2_get_client()
    if client is None:
        return None
    
    try:
        import orjson
        data_bytes = await client.get(f"dict:{word}")
        if data_bytes is None:
            return None
        
        if isinstance(data_bytes, bytes):
            data = orjson.loads(data_bytes)
        else:
            data = orjson.loads(data_bytes.encode("utf-8"))
        
        _l2_mark_recovered()
        logger.debug("L2 Redis cache hit: %s", word)
        return data
    except Exception as e:
        _l2_mark_failed()
        logger.warning("Redis GET failed: %s", e)
        return None


async def _l2_set_async(word: str, data: dict[str, Any]) -> None:
    """L2 Redis 缓存写入（使用项目全局连接池）"""
    client = await _l2_get_client()
    if client is None:
        return
    
    try:
        import orjson
        data_bytes = orjson.dumps(data)
        settings = get_settings()
        ttl = getattr(settings, "redis_cache_ttl", _L1_TTL_SECONDS)
        await client.setex(f"dict:{word}", ttl, data_bytes)
        _l2_mark_recovered()
        logger.debug("L2 Redis cache set: %s", word)
    except Exception as e:
        _l2_mark_failed()
        logger.warning("Redis SET failed: %s", e)


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
    client = await _l2_get_client()
    if client is None:
        return
    try:
        keys = await client.keys("dict:*")
        if keys:
            await client.delete(*keys)
        _l2_mark_recovered()
        logger.info("L2 cache cleared, %d keys deleted", len(keys))
    except Exception as e:
        _l2_mark_failed()
        logger.warning("Redis clear failed: %s", e)


def get_cache_stats() -> dict[str, Any]:
    """获取缓存统计信息（用于监控和调试）"""
    settings = get_settings()
    with _L1_LOCK:
        l1_size = len(_L1_CACHE)
    
    with _L2_FAILURE_LOCK:
        in_backoff = time.time() - _L2_LAST_FAILURE_TIME < _L2_FAILURE_BACKOFF_SECONDS
    
    return {
        "l1": {
            "size": l1_size,
            "max_size": _L1_MAX_SIZE,
            "ttl_seconds": _L1_TTL_SECONDS,
        },
        "l2": {
            "enabled": settings.redis_enabled,
            "in_backoff": in_backoff,
            "last_failure_time": _L2_LAST_FAILURE_TIME,
            "failure_backoff_seconds": _L2_FAILURE_BACKOFF_SECONDS,
        },
    }
