"""
应用程序入口模块。

负责创建和配置 FastAPI 应用实例，包括路由注册、生命周期管理等功能。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.config.settings import Settings, get_settings
from app.observability.langsmith import setup_langsmith


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    应用生命周期管理上下文管理器。

    在应用启动时初始化 LangSmith 追踪，避免在各个路由中重复处理。
    """
    setup_langsmith(get_settings())
    yield


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
