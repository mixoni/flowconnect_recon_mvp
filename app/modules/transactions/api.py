from __future__ import annotations
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.transactions.schemas import BankTransactionIn, BankImportResult
from app.modules.transactions.service import BankTransactionService

router = APIRouter(tags=["bank-transactions"])

@router.post("/tenants/{tenant_id}/bank-transactions/import", response_model=BankImportResult)
def import_bank_transactions(
    tenant_id: int,
    payload: list[BankTransactionIn],
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(get_session),
) -> BankImportResult:
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")
    result = BankTransactionService(session).import_bulk(tenant_id, idempotency_key, [p.model_dump() for p in payload])
    return BankImportResult(**result)
