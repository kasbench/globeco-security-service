from app.models.security import Security
from app.models.security_type import SecurityType
from app.schemas.security import SecurityIn, SecurityOut, SecurityTypeNested
from app.schemas.v2_security import SecurityV2, SecurityTypeNestedV2, SecuritySearchResponse, PaginationInfo
from typing import List, Optional
from beanie import PydanticObjectId
from fastapi import HTTPException
from bson import ObjectId
import math

async def get_all_securities() -> List[SecurityOut]:
    securities = await Security.find_all().to_list()
    result = []
    for sec in securities:
        st = await SecurityType.get(sec.security_type_id)
        if not st:
            raise HTTPException(status_code=400, detail="Invalid securityTypeId")
        result.append(SecurityOut(
            securityId=str(sec.id),
            ticker=sec.ticker,
            description=sec.description,
            securityTypeId=str(sec.security_type_id),
            version=sec.version,
            securityType=SecurityTypeNested(
                securityTypeId=str(st.id),
                abbreviation=st.abbreviation,
                description=st.description
            )
        ))
    return result

async def get_security(security_id: str) -> SecurityOut:
    sec = await Security.get(PydanticObjectId(security_id))
    if not sec:
        raise HTTPException(status_code=404, detail="Security not found")
    st = await SecurityType.get(sec.security_type_id)
    if not st:
        raise HTTPException(status_code=400, detail="Invalid securityTypeId")
    return SecurityOut(
        # securityId=str(sec.id),
        securityId = str(security_id),
        ticker=sec.ticker,
        description=sec.description,
        securityTypeId=str(sec.security_type_id),
        version=sec.version,
        securityType=SecurityTypeNested(
            securityTypeId=str(st.id),
            abbreviation=st.abbreviation,
            description=st.description
        )
    )

async def create_security(payload: SecurityIn) -> SecurityOut:
    st = await SecurityType.get(PydanticObjectId(payload.securityTypeId))
    if not st:
        raise HTTPException(status_code=400, detail="Invalid securityTypeId")
    sec = Security(
        ticker=payload.ticker,
        description=payload.description,
        security_type_id=ObjectId(payload.securityTypeId),
        version=payload.version
    )
    await sec.insert()
    return await get_security(str(sec.id))

async def update_security(security_id: str, payload: SecurityIn) -> SecurityOut:
    sec = await Security.get(PydanticObjectId(security_id))
    if not sec:
        raise HTTPException(status_code=404, detail="Security not found")
    if sec.version != payload.version:
        raise HTTPException(status_code=409, detail="Version conflict")
    st = await SecurityType.get(PydanticObjectId(payload.securityTypeId))
    if not st:
        raise HTTPException(status_code=400, detail="Invalid securityTypeId")
    sec.ticker = payload.ticker
    sec.description = payload.description
    sec.security_type_id = ObjectId(payload.securityTypeId)
    sec.version += 1
    await sec.save()
    return await get_security(str(sec.id))

async def delete_security(security_id: str, version: int):
    sec = await Security.get(PydanticObjectId(security_id))
    if not sec:
        raise HTTPException(status_code=404, detail="Security not found")
    if sec.version != version:
        raise HTTPException(status_code=409, detail="Version conflict")
    await sec.delete()

async def search_securities(
    ticker: Optional[str] = None,
    ticker_like: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> SecuritySearchResponse:
    """
    Search securities with pagination support.
    Supports exact ticker match or partial ticker search.
    """
    # Build query
    query = {}
    
    if ticker:
        # Exact match (case-insensitive)
        query["ticker"] = {"$regex": f"^{ticker}$", "$options": "i"}
    elif ticker_like:
        # Partial match (case-insensitive)
        query["ticker"] = {"$regex": ticker_like, "$options": "i"}
    
    # Get total count for pagination
    total_count = await Security.find(query).count()
    
    # Calculate pagination info
    total_pages = math.ceil(total_count / limit) if total_count > 0 else 0
    current_page = offset // limit
    has_next = (offset + limit) < total_count
    has_previous = offset > 0
    
    # Execute search with pagination and sorting
    securities = await Security.find(query).sort("ticker").skip(offset).limit(limit).to_list()
    
    # Build response with security type information
    result_securities = []
    for sec in securities:
        st = await SecurityType.get(sec.security_type_id)
        if not st:
            raise HTTPException(status_code=400, detail="Invalid securityTypeId")
        
        result_securities.append(SecurityV2(
            securityId=str(sec.id),
            ticker=sec.ticker,
            description=sec.description,
            securityTypeId=str(sec.security_type_id),
            version=sec.version,
            securityType=SecurityTypeNestedV2(
                securityTypeId=str(st.id),
                abbreviation=st.abbreviation,
                description=st.description,
                version=st.version
            )
        ))
    
    pagination = PaginationInfo(
        totalElements=total_count,
        totalPages=total_pages,
        currentPage=current_page,
        pageSize=limit,
        hasNext=has_next,
        hasPrevious=has_previous
    )
    
    return SecuritySearchResponse(
        securities=result_securities,
        pagination=pagination
    ) 