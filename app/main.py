import asyncio
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.config import settings
from app.models.security_type import SecurityType
from app.models.security import Security
from app.api.routes import router as api_router
from app.api.v2_routes import router as v2_api_router
from app.api.health import router as health_router
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="GlobeCo Security Service", version="1.0.0")

# Allow all origins for CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB]
    await init_beanie(database=db, document_models=[SecurityType, Security])
    
    # Create indexes for optimal search performance
    try:
        await Security.get_motor_collection().create_index("ticker")  # For exact matches
        await Security.get_motor_collection().create_index([("ticker", "text")])  # For text search
    except Exception as e:
        print(f"Index creation failed: {e}")  # Non-fatal for development

app.include_router(api_router)
app.include_router(v2_api_router)
app.include_router(health_router)

if os.environ.get("TEST_MODE") == "1":
    from app.api.utils_routes import router as test_utils_router
    app.include_router(test_utils_router)

if __name__ == "__main__":
    asyncio.run(on_startup())
