from fastapi import APIRouter, status, Response
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

router = APIRouter(prefix="/health")

@router.get("/liveness", status_code=status.HTTP_200_OK)
async def liveness():
    return {"status": "alive"}

@router.get("/readiness")
async def readiness(response: Response):
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=1000)
        await client.server_info()
        return {"status": "ready"}
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not ready"}

@router.get("/startup")
async def startup(response: Response):
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=1000)
        await client.server_info()
        return {"status": "started"}
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not started"} 