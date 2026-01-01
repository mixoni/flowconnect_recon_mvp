from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.invoices.schemas import InvoiceCreate, InvoiceOut
from app.modules.invoices.service import InvoiceService

router = APIRouter(tags=["invoices"])

@router.post("/tenants/{tenant_id}/invoices", response_model=InvoiceOut)
def create_invoice(tenant_id: int, payload: InvoiceCreate, session: Session = Depends(get_session)) -> InvoiceOut:
    return InvoiceService(session).create(tenant_id, **payload.model_dump())

@router.get("/tenants/{tenant_id}/invoices", response_model=list[InvoiceOut])
def list_invoices(
    tenant_id: int,
    status: str | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    session: Session = Depends(get_session),
) -> list[InvoiceOut]:
    return InvoiceService(session).list(
        tenant_id=tenant_id,
        status=status,
        amount_min=amount_min,
        amount_max=amount_max,
    )

@router.delete("/tenants/{tenant_id}/invoices/{invoice_id}")
def delete_invoice(tenant_id: int, invoice_id: int, session: Session = Depends(get_session)) -> dict:
    InvoiceService(session).delete(tenant_id, invoice_id)
    return {"deleted": True}
