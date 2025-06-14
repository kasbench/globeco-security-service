from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional
import re

class SecuritySearchParams(BaseModel):
    ticker: Optional[str] = Field(None, description="Exact ticker search (case-insensitive)")
    ticker_like: Optional[str] = Field(None, description="Partial ticker search (case-insensitive)")
    limit: int = Field(50, ge=1, le=1000, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Number of results to skip")

    @field_validator('ticker', 'ticker_like')
    @classmethod
    def validate_ticker_format(cls, v):
        if v is not None:
            if not re.match(r'^[A-Za-z0-9.-]{1,50}$', v):
                raise ValueError('Ticker must be 1-50 characters and contain only alphanumeric characters, dots, and hyphens')
        return v

    @model_validator(mode='after')
    def validate_mutual_exclusivity(self):
        if self.ticker is not None and self.ticker_like is not None:
            raise ValueError("Only one of 'ticker' or 'ticker_like' parameters can be provided")
        return self

class SecurityTypeNestedV2(BaseModel):
    securityTypeId: str
    abbreviation: str
    description: str
    version: int

class SecurityV2(BaseModel):
    securityId: str
    ticker: str
    description: str
    securityTypeId: str
    version: int
    securityType: SecurityTypeNestedV2

class PaginationInfo(BaseModel):
    totalElements: int
    totalPages: int
    currentPage: int
    pageSize: int
    hasNext: bool
    hasPrevious: bool

class SecuritySearchResponse(BaseModel):
    securities: List[SecurityV2]
    pagination: PaginationInfo 