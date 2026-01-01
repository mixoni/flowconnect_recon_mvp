from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.reconciliation.schemas import ReconcileRequest, MatchOut, ExplainOut
from app.modules.reconciliation.service import ReconciliationService, MatchService
from app.modules.reconciliation.ai import AIExplainService, ExplainContext
from app.modules.reconciliation.explain_service import ExplainService


router = APIRouter(tags=["reconciliation"])

def _match_to_out(m) -> MatchOut:
    return MatchOut(
        id=m.id,
        tenant_id=m.tenant_id,
        invoice_id=m.invoice_id,
        bank_transaction_id=m.bank_transaction_id,
        score=float(m.score),
        status=m.status,
        reasons=json.loads(m.reasons),
    )

@router.post("/tenants/{tenant_id}/reconcile", response_model=list[MatchOut])
def reconcile(
    tenant_id: int,
    req: ReconcileRequest = ReconcileRequest(),
    session: Session = Depends(get_session),
) -> list[MatchOut]:
    matches = ReconciliationService(session).reconcile(
        tenant_id=tenant_id,
        window_days=req.window_days,
        max_candidates_per_invoice=req.max_candidates_per_invoice,
    )
    return [_match_to_out(m) for m in matches]

@router.post("/tenants/{tenant_id}/matches/{match_id}/confirm", response_model=MatchOut)
def confirm_match(tenant_id: int, match_id: int, session: Session = Depends(get_session)) -> MatchOut:
    m = MatchService(session).confirm(tenant_id, match_id)
    return _match_to_out(m)

@router.get("/tenants/{tenant_id}/reconcile/explain", response_model=ExplainOut)
def explain(tenant_id: int, invoice_id: int, transaction_id: int, session: Session = Depends(get_session)) -> ExplainOut:
    # Gather deterministic context via reconciliation service helpers
    ctx = ExplainService(session).build_context(tenant_id, invoice_id, transaction_id)
    explainer = AIExplainService()
    text = explainer.explain_or_fallback(ctx)
    return ExplainOut(explanation=text)
