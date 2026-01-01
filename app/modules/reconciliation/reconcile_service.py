from __future__ import annotations

import json

from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from app.db.models import Invoice, BankTransaction, Match
from app.core.errors import BadRequestError
from app.modules.reconciliation.scoring import Candidate, score_match


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

            self.session.commit()

            for m in created:
                self.session.refresh(m)

            return created
        except Exception:
            self.session.rollback()
            raise
