from fastapi import APIRouter
from app.models.security import Security
from app.models.security_type import SecurityType

router = APIRouter()

@router.post("/test/cleanup")
async def cleanup_collections():
    await Security.get_motor_collection().drop()
    await SecurityType.get_motor_collection().drop()
    return {"status": "ok"} 