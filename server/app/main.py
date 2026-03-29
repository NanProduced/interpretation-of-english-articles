from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from app.api.router import api_router
from app.config.settings import get_settings


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    default_response_class=ORJSONResponse,
)
app.include_router(api_router)


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {
        "message": f"{settings.app_name} is running.",
        "env": settings.app_env,
    }

