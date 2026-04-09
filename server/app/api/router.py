from fastapi import APIRouter

from app.api.routes.analyze import router as analyze_router
from app.api.routes.auth import router as auth_router
from app.api.routes.dict import router as dict_router
from app.api.routes.favorites import router as favorites_router
from app.api.routes.health import router as health_router
from app.api.routes.quota import router as quota_router
from app.api.routes.records import router as records_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.vocabulary import router as vocabulary_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(analyze_router)
api_router.include_router(dict_router)
api_router.include_router(auth_router)
api_router.include_router(records_router)
api_router.include_router(tasks_router)
api_router.include_router(quota_router)
api_router.include_router(favorites_router)
api_router.include_router(vocabulary_router)

