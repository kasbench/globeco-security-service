from app.models.security import Security
from app.models.security_type import SecurityType
from app.schemas.security import SecurityIn, SecurityOut, SecurityUpdate, SecurityTypeNested
from typing import List, Optional
from beanie import PydanticObjectId
from fastapi import HTTPException, status
from bson import ObjectId

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