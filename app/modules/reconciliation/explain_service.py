from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import Invoice, BankTransaction
from app.core.errors import NotFoundError
from app.modules.reconciliation.ai import ExplainContext
from app.modules.reconciliation.scoring import score_match


class ExplainService:
    def __init__(self, session: Session):
        self.session = session

    def build_context(
        self,
        tenant_id: int,
        invoice_id: int,
        transaction_id: int,
        window_days: int = 3,
    ) -> ExplainContext:
        inv = self.session.scalars(
            select(Invoice).where(Invoice.tenant_id == tenant_id, Invoice.id == invoice_id)
        ).first()
        if not inv:
            raise NotFoundError("Invoice not found")

        tx = self.session.scalars(
            select(BankTransaction).where(
                BankTransaction.tenant_id == tenant_id, BankTransaction.id == transaction_id
            )
        ).first()
        if not tx:
            raise NotFoundError("Bank transaction not found")

        cand = score_match(inv, tx, window_days=window_days)
        score = float(cand.score) if cand else 0.0
        reasons = cand.reasons if cand else []

        return ExplainContext(
            invoice_amount=float(inv.amount),
            invoice_date=inv.invoice_date,
            invoice_description=inv.description,
            tx_amount=float(tx.amount),
            tx_posted_at=tx.posted_at,
            tx_description=tx.description,
            score=score,
            reasons=reasons,
        )
