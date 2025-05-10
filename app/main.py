import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.config import settings

async def init_db():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB]
    # Import your document models here and pass them to init_beanie
    # from app.models.security_type import SecurityType
    # from app.models.security import Security
    await init_beanie(database=db, document_models=[])

if __name__ == "__main__":
    asyncio.run(init_db())
