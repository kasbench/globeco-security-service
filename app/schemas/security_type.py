from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId

class SecurityTypeBase(BaseModel):
    abbreviation: str = Field(..., min_length=1, max_length=10)
    description: str = Field(..., min_length=1, max_length=100)
    version: int = Field(default=1)

class SecurityTypeIn(SecurityTypeBase):
    pass

class SecurityTypeOut(SecurityTypeBase):
    securityTypeId: str

    class Config:
        orm_mode = True

class SecurityTypeUpdate(SecurityTypeBase):
    securityTypeId: str 