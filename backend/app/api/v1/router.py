from fastapi import APIRouter

from app.api.v1 import auth, dashboard, knowledge, qa, search, settings, workspace

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(knowledge.router)
api_router.include_router(workspace.router)
api_router.include_router(search.router)
api_router.include_router(dashboard.router)
api_router.include_router(qa.router)
api_router.include_router(settings.router)
