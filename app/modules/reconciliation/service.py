from __future__ import annotations

import json
import datetime as dt
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from app.db.models import Invoice, BankTransaction, Match
from app.core.errors import NotFoundError, ConflictError, BadRequestError
from app.modules.reconciliation.ai import ExplainContext


@dataclass(frozen=True)
class Candidate:
    invoice_id: int
    bank_transaction_id: int
    score: float
    reasons: list[str]


def _text_score(a: str | None, b: str | None) -> tuple[float, list[str]]:
    a = (a or "").lower()
    b = (b or "").lower()
    if not a or not b:
        return 0.0, []
    reasons: list[str] = []
    if a in b or b in a:
        reasons.append("text_contains")
        return 15.0, reasons
    # lightweight overlap
    aset = {t for t in a.split() if len(t) > 3}
    bset = {t for t in b.split() if len(t) > 3}
    if not aset or not bset:
        return 0.0, []
    overlap = len(aset & bset) / max(len(aset), len(bset))
    if overlap > 0:
        reasons.append("text_overlap")
    return 15.0 * overlap, reasons


def score_match(invoice: Invoice, tx: BankTransaction, window_days: int = 3) -> Candidate | None:
    if invoice.currency != tx.currency:
        return None

    score = 0.0
    reasons: list[str] = []

    # Amount exact match
    if float(invoice.amount) == float(tx.amount):
        score += 60.0
        reasons.append("amount_exact")

    # Date proximity
    if invoice.invoice_date is not None:
        inv_dt = dt.datetime.combine(invoice.invoice_date, dt.time.min)
        diff_days = abs((tx.posted_at - inv_dt).days)
        if diff_days <= window_days:
            bonus = 25.0 * (1.0 - (diff_days / max(window_days, 1)))
            score += bonus
            reasons.append(f"date_within_{diff_days}_days")

    # Text heuristic
    text_bonus, text_reasons = _text_score(invoice.description, tx.description)
    if text_bonus > 0:
        score += text_bonus
        reasons.extend(text_reasons)

    return Candidate(
        invoice_id=invoice.id,
        bank_transaction_id=tx.id,
        score=round(score, 3),
        reasons=reasons,
    )


class ReconciliationService:
    def __init__(self, session: Session):
        self.session = session

    def reconcile(
        self,
        tenant_id: int,
        window_days: int = 3,
        max_candidates_per_invoice: int = 3,
    ) -> list[Match]:
        if window_days <= 0:
            raise BadRequestError("window_days must be > 0")
        if max_candidates_per_invoice <= 0:
            raise BadRequestError("max_candidates_per_invoice must be > 0")

        try:
            # Clear previous proposed matches for deterministic MVP behavior
            self.session.execute(
                delete(Match).where(Match.tenant_id == tenant_id, Match.status == "proposed")
            )

            invoices = list(
                self.session.scalars(
                    select(Invoice)
                    .where(Invoice.tenant_id == tenant_id, Invoice.status == "open")
                    .order_by(Invoice.id.asc())
                ).all()
            )
            txs = list(
                self.session.scalars(
                    select(BankTransaction)
                    .where(BankTransaction.tenant_id == tenant_id)
                    .order_by(BankTransaction.id.asc())
                ).all()
            )

            created: list[Match] = []
            seen_pairs: set[tuple[int, int]] = set()

            for inv in invoices:
                cands: list[Candidate] = []
                for tx in txs:
                    cand = score_match(inv, tx, window_days=window_days)
                    if cand and cand.score > 0:
                        cands.append(cand)

                cands.sort(key=lambda c: (-c.score, c.bank_transaction_id))

                for cand in cands[:max_candidates_per_invoice]:
                    pair = (cand.invoice_id, cand.bank_transaction_id)
                    if pair in seen_pairs:
                        continue
                    seen_pairs.add(pair)

                    m = Match(
                        tenant_id=tenant_id,
                        invoice_id=cand.invoice_id,
                        bank_transaction_id=cand.bank_transaction_id,
                        score=cand.score,
                        status="proposed",
                        reasons=json.dumps(cand.reasons),
                    )
                    self.session.add(m)
                    created.append(m)

            # Single commit for delete + inserts
            self.session.commit()

            # refresh IDs
            for m in created:
                self.session.refresh(m)

            return created
        except Exception:
            self.session.rollback()
            raise

    def build_explain_context(
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


class MatchService:
    def __init__(self, session: Session):
        self.session = session

    def confirm(self, tenant_id: int, match_id: int) -> Match:
        match = self.session.scalars(
            select(Match).where(Match.tenant_id == tenant_id, Match.id == match_id)
        ).first()
        if not match:
            raise NotFoundError("Match not found")

        if match.status != "proposed":
            raise BadRequestError(f"Match is not in proposed state (current={match.status})")

        # ensure only one confirmed match per invoice
        existing_confirmed = self.session.scalars(
            select(Match).where(
                Match.tenant_id == tenant_id,
                Match.invoice_id == match.invoice_id,
                Match.status == "confirmed",
            )
        ).first()
        if existing_confirmed and existing_confirmed.id != match.id:
            raise ConflictError("Invoice already has a confirmed match")

        match.status = "confirmed"

        inv = self.session.scalars(
            select(Invoice).where(Invoice.tenant_id == tenant_id, Invoice.id == match.invoice_id)
        ).first()
        if not inv:
            raise NotFoundError("Invoice not found")

        inv.status = "matched"

        try:
            self.session.commit()
            self.session.refresh(match)
            return match
        except Exception:
            self.session.rollback()
            raise
