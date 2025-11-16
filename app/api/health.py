from fastapi import APIRouter, status, Response
from beanie import init_beanie
from app.config import settings
import logging

router = APIRouter(prefix="/health")
logger = logging.getLogger(__name__)

@router.get("/liveness", status_code=status.HTTP_200_OK)
async def liveness():
    """Liveness probe - returns OK if the service is running."""
    return {"status": "alive"}

@router.get("/readiness")
async def readiness(response: Response):
    """Readiness probe - checks if MongoDB connection is healthy."""
    try:
        # Use Beanie's existing connection instead of creating a new client
        from app.models.security import Security
        
        # Quick ping to verify connection (uses existing connection pool)
        await Security.get_motor_collection().database.command('ping')
        return {"status": "ready"}
    except Exception as e:
        logger.warning(f"Readiness check failed: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not ready", "error": str(e)}

@router.get("/startup")
async def startup(response: Response):
    """Startup probe - checks if MongoDB connection is established."""
    try:
        # Use Beanie's existing connection instead of creating a new client
        from app.models.security import Security
        
        # Quick ping to verify connection (uses existing connection pool)
        await Security.get_motor_collection().database.command('ping')
        return {"status": "started"}
    except Exception as e:
        logger.warning(f"Startup check failed: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not started", "error": str(e)} 