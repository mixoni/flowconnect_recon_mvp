from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models import Tenant
from app.core.errors import NotFoundError

class TenantService:
    def __init__(self, session: Session):
        self.session = session

    def create(self, name: str) -> Tenant:
        tenant = Tenant(name=name)
        self.session.add(tenant)
        self.session.commit()
        self.session.refresh(tenant)
        return tenant

    def list(self) -> list[Tenant]:
        return list(self.session.scalars(select(Tenant).order_by(Tenant.id.asc())).all())

    def get(self, tenant_id: int) -> Tenant:
        t = self.session.get(Tenant, tenant_id)
        if not t:
            raise NotFoundError("Tenant not found")
        return t
