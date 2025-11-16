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
    
    # Batch fetch all security types to avoid N+1 queries
    security_type_ids = list(set(sec.security_type_id for sec in securities))
    security_types = await SecurityType.find({"_id": {"$in": security_type_ids}}).to_list()
    security_types_map = {st.id: st for st in security_types}
    
    result = []
    for sec in securities:
        st = security_types_map.get(sec.security_type_id)
        if not st:
            raise HTTPException(status_code=400, detail=f"Invalid securityTypeId: {sec.security_type_id}")
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
    # Use aggregation pipeline to fetch security and security type in a single query
    pipeline = [
        {"$match": {"_id": PydanticObjectId(security_id)}},
        {
            "$lookup": {
                "from": "securityType",
                "localField": "security_type_id",
                "foreignField": "_id",
                "as": "security_type"
            }
        },
        {"$unwind": "$security_type"}
    ]
    
    result = await Security.get_motor_collection().aggregate(pipeline).to_list(length=1)
    
    if not result:
        raise HTTPException(status_code=404, detail="Security not found")
    
    sec_data = result[0]
    st_data = sec_data.get("security_type")
    
    if not st_data:
        raise HTTPException(status_code=400, detail="Invalid securityTypeId")
    
    return SecurityOut(
        securityId=str(sec_data["_id"]),
        ticker=sec_data["ticker"],
        description=sec_data["description"],
        securityTypeId=str(sec_data["security_type_id"]),
        version=sec_data["version"],
        securityType=SecurityTypeNested(
            securityTypeId=str(st_data["_id"]),
            abbreviation=st_data["abbreviation"],
            description=st_data["description"]
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
    
    # Batch fetch all security types to avoid N+1 queries
    security_type_ids = list(set(sec.security_type_id for sec in securities))
    security_types = await SecurityType.find({"_id": {"$in": security_type_ids}}).to_list()
    security_types_map = {st.id: st for st in security_types}
    
    # Build response with security type information
    result_securities = []
    for sec in securities:
        st = security_types_map.get(sec.security_type_id)
        if not st:
            raise HTTPException(status_code=400, detail=f"Invalid securityTypeId: {sec.security_type_id}")
        
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