import asyncio
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.config import settings
from app.models.security_type import SecurityType
from app.models.security import Security
from app.api.routes import router as api_router
import os

app = FastAPI(title="GlobeCo Security Service", version="1.0.0")

@app.on_event("startup")
async def on_startup():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB]
    await init_beanie(database=db, document_models=[SecurityType, Security])

app.include_router(api_router)

if os.environ.get("TEST_MODE") == "1":
    from app.api.utils_routes import router as test_utils_router
    app.include_router(test_utils_router)

if __name__ == "__main__":
    asyncio.run(on_startup())
