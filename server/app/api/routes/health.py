from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.config.settings import get_settings
from app.database.connection import is_db_ready, is_redis_ready

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check(request: Request) -> dict[str, str | bool | int]:
    """
    健康检查端点。

    返回应用状态、PostgreSQL 连接状态、Redis 连接状态、worker 状态。
    Redis 状态仅供参考，不影响整体状态（因为 Redis 是可选增强）。
    """
    settings = get_settings()
    db_ready = await is_db_ready()
    redis_ready = await is_redis_ready()
    worker_snapshot = _get_worker_snapshot(request)
    worker_ready = bool(worker_snapshot["healthy"])

    return {
        "status": "ok" if db_ready and worker_ready else "degraded",
        "app": settings.app_name,
        "env": settings.app_env,
        "postgres": db_ready,
        "redis": redis_ready,
        "worker": worker_ready,
        "worker_inflight_tasks": int(worker_snapshot["inflight_tasks"]),
    }


@router.get("/db")
async def db_health() -> dict[str, str | bool]:
    """数据库连接健康检查。"""
    db_ready = await is_db_ready()
    return {
        "status": "ok" if db_ready else "unavailable",
        "postgres": db_ready,
    }


@router.get("/ready")
async def readiness_check(request: Request) -> dict[str, str | bool | int]:
    """
    Readiness probe.

    仅当 PostgreSQL 和 analysis task worker 都健康时返回 200。
    否则返回 503，供容器 / LB 摘流。
    """
    db_ready = await is_db_ready()
    worker_snapshot = _get_worker_snapshot(request)
    worker_ready = bool(worker_snapshot["healthy"])

    if not db_ready or not worker_ready:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unavailable",
                "postgres": db_ready,
                "worker": worker_ready,
                "worker_inflight_tasks": int(worker_snapshot["inflight_tasks"]),
            },
        )

    return {
        "status": "ok",
        "postgres": db_ready,
        "worker": worker_ready,
        "worker_inflight_tasks": int(worker_snapshot["inflight_tasks"]),
    }


def _get_worker_snapshot(request: Request) -> dict[str, bool | int | str]:
    worker = getattr(request.app.state, "analysis_task_worker", None)
    if worker is None:
        return {
            "healthy": False,
            "worker_token": "",
            "runner_running": False,
            "stopping": True,
            "inflight_tasks": 0,
        }
    return worker.health_snapshot()
