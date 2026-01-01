from __future__ import annotations
import json
import strawberry
from sqlalchemy.orm import Session

from app.modules.reconciliation.service import ReconciliationService, MatchService
from app.modules.reconciliation.ai import AIExplainService

@strawberry.type
class MatchType:
    id: int
    tenant_id: int
    invoice_id: int
    bank_transaction_id: int
    score: float
    status: str
    reasons: list[str]

@strawberry.type
class ExplainType:
    explanation: str

@strawberry.type
class ReconciliationQuery:
    @strawberry.field
    def explain_reconciliation(self, info, tenant_id: int, invoice_id: int, transaction_id: int) -> ExplainType:
        session: Session = info.context["session"]
        ctx = ReconciliationService(session).build_explain_context(tenant_id, invoice_id, transaction_id)
        text = AIExplainService().explain_or_fallback(ctx)
        return ExplainType(explanation=text)

@strawberry.type
class ReconciliationMutation:
    @strawberry.mutation
    def reconcile(self, info, tenant_id: int, window_days: int = 3, max_candidates_per_invoice: int = 3) -> list[MatchType]:
        session: Session = info.context["session"]
        matches = ReconciliationService(session).reconcile(tenant_id, window_days, max_candidates_per_invoice)
        return [MatchType(
            id=m.id,
            tenant_id=m.tenant_id,
            invoice_id=m.invoice_id,
            bank_transaction_id=m.bank_transaction_id,
            score=float(m.score),
            status=m.status,
            reasons=json.loads(m.reasons),
        ) for m in matches]

    @strawberry.mutation
    def confirm_match(self, info, tenant_id: int, match_id: int) -> MatchType:
        session: Session = info.context["session"]
        m = MatchService(session).confirm(tenant_id, match_id)
        return MatchType(
            id=m.id,
            tenant_id=m.tenant_id,
            invoice_id=m.invoice_id,
            bank_transaction_id=m.bank_transaction_id,
            score=float(m.score),
            status=m.status,
            reasons=json.loads(m.reasons),
        )
