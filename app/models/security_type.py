from beanie import Document
from pydantic import Field

class SecurityType(Document):
    abbreviation: str = Field(..., min_length=1, max_length=10, description="Unique abbreviation")
    description: str = Field(..., min_length=1, max_length=100, description="Description of the security type")
    version: int = Field(default=1, description="Optimistic concurrency version")

    class Settings:
        name = "securityType"

    class Config:
        schema_extra = {
            "example": {
                "abbreviation": "EQ",
                "description": "Equity security type",
                "version": 1
            }
        } 