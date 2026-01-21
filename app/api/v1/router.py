from fastapi import APIRouter
from app.api.v1.endpoints import complaints, documents, summaries, health

api_router = APIRouter()

api_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"]
)
api_router.include_router(
    complaints.router,
    prefix="/complaints",
    tags=["complaints"]
)
api_router.include_router(
    documents.router,
    tags=["documents"]
)
api_router.include_router(
    summaries.router,
    prefix="/summaries",
    tags=["summaries"]
)
