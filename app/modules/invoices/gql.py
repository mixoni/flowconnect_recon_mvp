from __future__ import annotations
import datetime as dt
import strawberry
from sqlalchemy.orm import Session

from app.modules.invoices.service import InvoiceService

@strawberry.type
class InvoiceType:
    id: int
    tenant_id: int
    amount: float
    currency: str
    invoice_date: str | None
    description: str | None
    status: str

@strawberry.input
class CreateInvoiceInput:
    amount: float
    currency: str = "USD"
    invoice_date: str | None = None
    description: str | None = None

@strawberry.type
class InvoicesQuery:
    @strawberry.field
    def invoices(
        self,
        info,
        tenant_id: int,
        status: str | None = None,
        amount_min: float | None = None,
        amount_max: float | None = None,
    ) -> list[InvoiceType]:
        session: Session = info.context["session"]
        items = InvoiceService(session).list(tenant_id, status=status, amount_min=amount_min, amount_max=amount_max)
        return [
            InvoiceType(
                id=i.id,
                tenant_id=i.tenant_id,
                amount=float(i.amount),
                currency=i.currency,
                invoice_date=i.invoice_date.isoformat() if i.invoice_date else None,
                description=i.description,
                status=i.status,
            )
            for i in items
        ]

@strawberry.type
class InvoicesMutation:
    @strawberry.mutation
    def create_invoice(self, info, tenant_id: int, input: CreateInvoiceInput) -> InvoiceType:
        session: Session = info.context["session"]
        inv_date = dt.date.fromisoformat(input.invoice_date) if input.invoice_date else None
        inv = InvoiceService(session).create(tenant_id, amount=input.amount, currency=input.currency, invoice_date=inv_date, description=input.description)
        return InvoiceType(
            id=inv.id,
            tenant_id=inv.tenant_id,
            amount=float(inv.amount),
            currency=inv.currency,
            invoice_date=inv.invoice_date.isoformat() if inv.invoice_date else None,
            description=inv.description,
            status=inv.status,
        )

    @strawberry.mutation
    def delete_invoice(self, info, tenant_id: int, invoice_id: int) -> bool:
        session: Session = info.context["session"]
        InvoiceService(session).delete(tenant_id, invoice_id)
        return True
