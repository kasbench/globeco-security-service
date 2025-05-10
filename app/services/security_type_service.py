from app.models.security_type import SecurityType
from app.schemas.security_type import SecurityTypeIn, SecurityTypeOut
from typing import List
from beanie import PydanticObjectId
from fastapi import HTTPException

async def get_all_security_types() -> List[SecurityTypeOut]:
    security_types = await SecurityType.find_all().to_list()
    return [SecurityTypeOut(
        securityTypeId=str(st.id),
        abbreviation=st.abbreviation,
        description=st.description,
        version=st.version
    ) for st in security_types]

async def get_security_type(security_type_id: str) -> SecurityTypeOut:
    st = await SecurityType.get(PydanticObjectId(security_type_id))
    if not st:
        raise HTTPException(status_code=404, detail="SecurityType not found")
    return SecurityTypeOut(
        securityTypeId=str(st.id),
        abbreviation=st.abbreviation,
        description=st.description,
        version=st.version
    )

async def create_security_type(data: SecurityTypeIn) -> SecurityTypeOut:
    st = SecurityType(**data.dict())
    await st.insert()
    return SecurityTypeOut(
        securityTypeId=str(st.id),
        abbreviation=st.abbreviation,
        description=st.description,
        version=st.version
    )

async def update_security_type(security_type_id: str, data: SecurityTypeIn) -> SecurityTypeOut:
    st = await SecurityType.get(PydanticObjectId(security_type_id))
    if not st:
        raise HTTPException(status_code=404, detail="SecurityType not found")
    # Optimistic concurrency check
    if st.version != data.version:
        raise HTTPException(status_code=409, detail="Version conflict")
    st.abbreviation = data.abbreviation
    st.description = data.description
    st.version += 1
    await st.save()
    return SecurityTypeOut(
        securityTypeId=str(st.id),
        abbreviation=st.abbreviation,
        description=st.description,
        version=st.version
    )

async def delete_security_type(security_type_id: str, version: int):
    st = await SecurityType.get(PydanticObjectId(security_type_id))
    if not st:
        raise HTTPException(status_code=404, detail="SecurityType not found")
    if st.version != version:
        raise HTTPException(status_code=409, detail="Version conflict")
    await st.delete() 