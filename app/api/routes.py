from fastapi import APIRouter, Query
from typing import List
from app.schemas.security_type import SecurityTypeIn, SecurityTypeOut
from app.services import security_type_service
from app.schemas.security import SecurityIn, SecurityOut
from app.services import security_service

router = APIRouter(prefix="/api/v1")

@router.get("/securityTypes", response_model=List[SecurityTypeOut])
async def get_security_types():
    return await security_type_service.get_all_security_types()

@router.get("/securityType/{securityTypeId}", response_model=SecurityTypeOut)
async def get_security_type(securityTypeId: str):
    return await security_type_service.get_security_type(securityTypeId)

@router.post("/securityTypes", response_model=SecurityTypeOut, status_code=201)
async def create_security_type(payload: SecurityTypeIn):
    return await security_type_service.create_security_type(payload)

@router.put("/securityType/{securityTypeId}", response_model=SecurityTypeOut)
async def update_security_type(securityTypeId: str, payload: SecurityTypeIn):
    return await security_type_service.update_security_type(securityTypeId, payload)

@router.delete("/securityType/{securityTypeId}", status_code=204)
async def delete_security_type(securityTypeId: str, version: int = Query(...)):
    await security_type_service.delete_security_type(securityTypeId, version)

@router.get("/securities", response_model=List[SecurityOut])
async def get_securities():
    return await security_service.get_all_securities()

@router.get("/security/{securityId}", response_model=SecurityOut)
async def get_security(securityId: str):
    return await security_service.get_security(securityId)

@router.post("/securities", response_model=SecurityOut, status_code=201)
async def create_security(payload: SecurityIn):
    return await security_service.create_security(payload)

@router.put("/security/{securityId}", response_model=SecurityOut)
async def update_security(securityId: str, payload: SecurityIn):
    return await security_service.update_security(securityId, payload)

@router.delete("/security/{securityId}", status_code=204)
async def delete_security(securityId: str, version: int):
    await security_service.delete_security(securityId, version) 