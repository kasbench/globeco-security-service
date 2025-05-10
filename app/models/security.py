from beanie import Document
from pydantic import Field, ConfigDict
from typing import Optional
from bson import ObjectId

class Security(Document):
    ticker: str = Field(..., min_length=1, max_length=50, description="Unique ticker")
    description: str = Field(..., min_length=1, max_length=200, description="Description of the security")
    security_type_id: ObjectId = Field(..., description="Foreign key to securityType")
    version: int = Field(default=1, description="Optimistic concurrency version")

    model_config = ConfigDict(arbitrary_types_allowed=True, json_schema_extra={
        "example": {
            "ticker": "AAPL",
            "description": "Apple Inc. equity",
            "security_type_id": "60c72b2f9b1e8b3f8c8b4567",
            "version": 1
        }
    })

    class Settings:
        name = "security" 