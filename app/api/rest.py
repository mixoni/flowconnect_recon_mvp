from __future__ import annotations
from fastapi import APIRouter

from app.modules.tenants.api import router as tenants_router
from app.modules.invoices.api import router as invoices_router
from app.modules.transactions.api import router as transactions_router
from app.modules.reconciliation.api import router as reconciliation_router

router = APIRouter()

router.include_router(tenants_router)
router.include_router(invoices_router)
router.include_router(transactions_router)
router.include_router(reconciliation_router)
