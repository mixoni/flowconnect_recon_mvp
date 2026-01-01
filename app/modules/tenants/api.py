from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.tenants.schemas import TenantCreate, TenantOut
from app.modules.tenants.service import TenantService

router = APIRouter(tags=["tenants"])

@router.post("/tenants", response_model=TenantOut)
def create_tenant(payload: TenantCreate, session: Session = Depends(get_session)) -> TenantOut:
    return TenantService(session).create(payload.name)

@router.get("/tenants", response_model=list[TenantOut])
def list_tenants(session: Session = Depends(get_session)) -> list[TenantOut]:
    return TenantService(session).list()
