from __future__ import annotations
from pydantic import BaseModel
from pydantic import ConfigDict

class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: int
    invoice_id: int
    bank_transaction_id: int
    score: float
    status: str
    reasons: list[str]

class ReconcileRequest(BaseModel):
    window_days: int = 3
    max_candidates_per_invoice: int = 3

class ExplainOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    explanation: str
