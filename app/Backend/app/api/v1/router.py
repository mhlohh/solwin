from fastapi import APIRouter

from app.api.v1.analysis import router as analysis_router
from app.api.v1.attachments import router as attachments_router
from app.api.v1.auth import router as auth_router
from app.api.v1.campaigns import router as campaigns_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.dashboard import analytics_router, dashboard_router
from app.api.v1.security import router as security_router
from app.api.v1.unified import router as unified_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(conversations_router)
api_v1_router.include_router(attachments_router)
api_v1_router.include_router(analysis_router)
api_v1_router.include_router(security_router)
api_v1_router.include_router(unified_router)
api_v1_router.include_router(campaigns_router)
api_v1_router.include_router(dashboard_router)
api_v1_router.include_router(analytics_router)
