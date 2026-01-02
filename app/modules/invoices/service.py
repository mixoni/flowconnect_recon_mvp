from __future__ import annotations
import datetime as dt
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from app.db.models import Invoice
from app.core.errors import NotFoundError, BadRequestError

class InvoiceService:
    def __init__(self, session: Session):
        self.session = session

    def create(self, tenant_id: int, amount: float, currency: str="USD",
               invoice_date: dt.date | None=None, description: str | None=None) -> Invoice:

        if amount <= 0:
            raise BadRequestError("Invoice amount must be > 0")

        inv = Invoice(
            tenant_id=tenant_id,
            amount=amount,
            currency=currency,
            invoice_date=invoice_date,
            description=description,
            status="open",
        )
        self.session.add(inv)
        self.session.commit()
        self.session.refresh(inv)
        return inv

    def list(self, tenant_id: int, status: str | None=None,
             amount_min: float | None=None, amount_max: float | None=None) -> list[Invoice]:
        stmt = select(Invoice).where(Invoice.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(Invoice.status == status)
        if amount_min is not None:
            stmt = stmt.where(Invoice.amount >= amount_min)
        if amount_max is not None:
            stmt = stmt.where(Invoice.amount <= amount_max)
        stmt = stmt.order_by(Invoice.id.asc())
        return list(self.session.scalars(stmt).all())

    def get(self, tenant_id: int, invoice_id: int) -> Invoice:
        stmt = select(Invoice).where(Invoice.tenant_id == tenant_id, Invoice.id == invoice_id)
        inv = self.session.scalars(stmt).first()
        if not inv:
            raise NotFoundError("Invoice not found")
        return inv

    def delete(self, tenant_id: int, invoice_id: int) -> None:
        # Ensure tenant ownership
        self.get(tenant_id, invoice_id)
        self.session.execute(delete(Invoice).where(Invoice.tenant_id == tenant_id, Invoice.id == invoice_id))
        self.session.commit()
