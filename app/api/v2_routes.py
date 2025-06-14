from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
from app.schemas.v2_security import SecuritySearchParams, SecuritySearchResponse
from app.services import security_service

router = APIRouter(prefix="/api/v2")

def validate_search_params(
    ticker: Optional[str] = Query(None, description="Exact ticker search (case-insensitive)"),
    ticker_like: Optional[str] = Query(None, description="Partial ticker search (case-insensitive)"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip")
) -> SecuritySearchParams:
    """
    Validate search parameters and ensure mutual exclusivity.
    """
    try:
        return SecuritySearchParams(
            ticker=ticker,
            ticker_like=ticker_like,
            limit=limit,
            offset=offset
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/securities", response_model=SecuritySearchResponse)
async def search_securities(params: SecuritySearchParams = Depends(validate_search_params)):
    """
    Search securities with advanced filtering and pagination.
    
    - **ticker**: Exact ticker match (case-insensitive)
    - **ticker_like**: Partial ticker match (case-insensitive)  
    - **limit**: Maximum results per page (1-1000, default: 50)
    - **offset**: Number of results to skip (default: 0)
    
    Only one of ticker or ticker_like can be provided.
    If neither is provided, returns all securities with pagination.
    """
    return await security_service.search_securities(
        ticker=params.ticker,
        ticker_like=params.ticker_like,
        limit=params.limit,
        offset=params.offset
    )