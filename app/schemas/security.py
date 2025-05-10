from pydantic import BaseModel, Field

class SecurityBase(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., min_length=1, max_length=200)
    securityTypeId: str
    version: int = Field(default=1)

class SecurityIn(SecurityBase):
    pass

class SecurityTypeNested(BaseModel):
    securityTypeId: str
    abbreviation: str
    description: str

class SecurityOut(SecurityBase):
    securityId: str
    securityType: SecurityTypeNested

    class Config:
        orm_mode = True

class SecurityUpdate(SecurityBase):
    securityId: str 