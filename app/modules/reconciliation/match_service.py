from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import Invoice, Match
from app.core.errors import NotFoundError, ConflictError, BadRequestError


class MatchService:
    def __init__(self, session: Session):
        self.session = session

    def confirm(self, tenant_id: int, match_id: int) -> Match:
        match = self.session.scalars(
            select(Match).where(
                Match.tenant_id == tenant_id,
                Match.id == match_id,
            )
        ).first()

        if not match:
            raise NotFoundError("Match not found")

        if match.status != "proposed":
            raise BadRequestError(
                f"Match is not in proposed state (current={match.status})"
            )

        # Ensure only one confirmed match per invoice
        existing_confirmed = self.session.scalars(
            select(Match).where(
                Match.tenant_id == tenant_id,
                Match.invoice_id == match.invoice_id,
                Match.status == "confirmed",
            )
        ).first()

        if existing_confirmed and existing_confirmed.id != match.id:
            raise ConflictError("Invoice already has a confirmed match")

        # Update match
        match.status = "confirmed"

        # Update invoice
        invoice = self.session.scalars(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.id == match.invoice_id,
            )
        ).first()

        if not invoice:
            raise NotFoundError("Invoice not found")

        invoice.status = "matched"

        try:
            self.session.commit()
            self.session.refresh(match)
            return match
        except Exception:
            self.session.rollback()
            raise
