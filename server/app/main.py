"""
应用程序入口模块。

负责创建和配置 FastAPI 应用实例，包括路由注册、生命周期管理等功能。
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from logging import getLogger

from fastapi import FastAPI

from app.api.router import api_router
from app.config.settings import Settings, get_settings
from app.database.connection import close_db, close_redis, init_db, init_redis
from app.observability.langsmith import setup_langsmith

logger = getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """
    应用生命周期管理上下文管理器。

    启动时：初始化 PostgreSQL 连接池（必选）、Redis 连接（可选）
    关闭时：清理所有连接池
    """
    settings = get_settings()

    # 1. 初始化 PostgreSQL（必选）
    try:
        await init_db(
            database_url=settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
            max_inactive_connection_lifetime=settings.database_max_inactive_connection_lifetime,
        )
        logger.info("PostgreSQL pool initialized")
    except Exception as e:
        logger.error("Failed to initialize PostgreSQL pool: %s", e)
        raise

    # 2. 初始化 Redis（可选，第二阶段增强）
    await init_redis(redis_url=settings.redis_url, enabled=settings.redis_enabled)

    # 3. 初始化 LangSmith
    setup_langsmith(settings)

    # 4. 恢复服务重启前残留的活跃任务（标记为 failed，允许用户重试）
    try:
        from app.services.analysis.task_executor import recover_stuck_tasks

        recovered = await recover_stuck_tasks()
        if recovered:
            logger.info("Recovered %d stuck tasks on startup", recovered)
    except Exception as e:
        logger.warning("Failed to recover stuck tasks on startup: %s", e)

    yield

    # 关闭时清理
    await close_redis()
    await close_db()
    logger.info("Application shutdown complete")


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    创建并配置 FastAPI 应用实例。

    Args:
        settings: 可选的应用程序配置对象。如果未提供，则从环境变量加载默认配置。

    Returns:
        配置完成的 FastAPI 应用实例
    """
    active_settings = settings or get_settings()
    app = FastAPI(
        title=active_settings.app_name,
        lifespan=lifespan,
    )
    app.include_router(api_router)

    @app.get("/", tags=["system"])
    async def root() -> dict[str, str]:
        """
        根路径健康检查端点。

        返回应用名称和运行环境信息。
        """
        return {
            "message": f"{active_settings.app_name} is running.",
            "env": active_settings.app_env,
        }

    return app


# 创建应用实例，供 uvicorn 等服务器使用
app = create_app()
