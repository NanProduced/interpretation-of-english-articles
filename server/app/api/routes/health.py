from __future__ import annotations

from fastapi import APIRouter

from app.config.settings import get_settings
from app.database.connection import is_db_ready, is_redis_ready

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check() -> dict[str, str | bool]:
    """
    健康检查端点。

    返回应用状态、PostgreSQL 连接状态、Redis 连接状态。
    Redis 状态仅供参考，不影响整体状态（因为 Redis 是可选增强）。
    """
    settings = get_settings()
    db_ready = await is_db_ready()
    redis_ready = await is_redis_ready()

    return {
        "status": "ok" if db_ready else "degraded",
        "app": settings.app_name,
        "env": settings.app_env,
        "postgres": db_ready,
        "redis": redis_ready,
    }


@router.get("/db")
async def db_health() -> dict[str, str | bool]:
    """数据库连接健康检查。"""
    db_ready = await is_db_ready()
    return {
        "status": "ok" if db_ready else "unavailable",
        "postgres": db_ready,
    }

