from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from app.api.router import api_router
from app.config.settings import Settings, get_settings
from app.observability.langsmith import setup_langsmith


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 应用启动时统一初始化 LangSmith，避免在各个路由里重复处理。
    setup_langsmith(get_settings())
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    app = FastAPI(
        title=active_settings.app_name,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )
    app.include_router(api_router)

    @app.get("/", tags=["system"])
    async def root() -> dict[str, str]:
        return {
            "message": f"{active_settings.app_name} is running.",
            "env": active_settings.app_env,
        }

    return app


app = create_app()
