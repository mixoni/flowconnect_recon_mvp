from __future__ import annotations
import datetime as dt
from pydantic import BaseModel
from pydantic import ConfigDict

class InvoiceCreate(BaseModel):
    amount: float
    currency: str = "USD"
    invoice_date: dt.date | None = None
    description: str | None = None

class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: int
    amount: float
    currency: str
    invoice_date: dt.date | None
    description: str | None
    status: str
    created_at: dt.datetime
