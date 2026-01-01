from __future__ import annotations
import strawberry
from sqlalchemy.orm import Session

from app.modules.tenants.service import TenantService

@strawberry.type
class TenantType:
    id: int
    name: str

@strawberry.input
class CreateTenantInput:
    name: str

@strawberry.type
class TenantsQuery:
    @strawberry.field
    def tenants(self, info) -> list[TenantType]:
        session: Session = info.context["session"]
        items = TenantService(session).list()
        return [TenantType(id=t.id, name=t.name) for t in items]

@strawberry.type
class TenantsMutation:
    @strawberry.mutation
    def create_tenant(self, info, input: CreateTenantInput) -> TenantType:
        session: Session = info.context["session"]
        t = TenantService(session).create(input.name)
        return TenantType(id=t.id, name=t.name)
