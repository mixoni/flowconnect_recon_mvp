from __future__ import annotations
import datetime as dt
from pydantic import BaseModel, Field
from pydantic import ConfigDict

class BankTransactionIn(BaseModel):
    external_id: str | None = Field(default=None, max_length=200)
    posted_at: dt.datetime
    amount: float
    currency: str = "USD"
    description: str = Field(min_length=1, max_length=500)

class BankImportResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    imported: int
    deduped: int = 0
    # Extra fields (not required by tests, but useful)
    duplicate_external_ids: int = 0
    transaction_ids: list[int] = []
