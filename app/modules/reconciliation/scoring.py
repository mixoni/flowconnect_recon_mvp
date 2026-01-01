from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from app.db.models import Invoice, BankTransaction


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

    if float(invoice.amount) == float(tx.amount):
        score += 60.0
        reasons.append("amount_exact")

    if invoice.invoice_date is not None:
        inv_dt = dt.datetime.combine(invoice.invoice_date, dt.time.min)
        diff_days = abs((tx.posted_at - inv_dt).days)
        if diff_days <= window_days:
            bonus = 25.0 * (1.0 - (diff_days / max(window_days, 1)))
            score += bonus
            reasons.append(f"date_within_{diff_days}_days")

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
