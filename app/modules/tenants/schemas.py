from __future__ import annotations
import datetime as dt
from pydantic import BaseModel, Field
from pydantic import ConfigDict

class TenantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)

class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    created_at: dt.datetime
