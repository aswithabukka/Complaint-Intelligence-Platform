from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis

from app.db.session import get_db
from app.core.config import settings

router = APIRouter()


@router.get("/health", summary="Health check")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


@router.get("/health/ready", summary="Readiness check")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness check that verifies database and Redis connectivity.
    """
    checks = {
        "database": False,
        "redis": False
    }

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        checks["database"] = str(e)

    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        checks["redis"] = True
    except Exception as e:
        checks["redis"] = str(e)

    all_healthy = all(v is True for v in checks.values())

    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks
    }
