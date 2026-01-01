from __future__ import annotations
import datetime as dt
import strawberry
from sqlalchemy.orm import Session

from app.modules.transactions.service import BankTransactionService

@strawberry.input
class BankTransactionInput:
    external_id: str | None = None
    posted_at: str
    amount: float
    currency: str = "USD"
    description: str

@strawberry.type
class BankImportResultType:
    deduped: int
    imported: int
    duplicate_external_ids: int
    transaction_ids: list[int]

@strawberry.type
class TransactionsMutation:
    @strawberry.mutation
    def import_bank_transactions(self, info, tenant_id: int, input: list[BankTransactionInput], idempotency_key: str) -> BankImportResultType:
        session: Session = info.context["session"]
        items = []
        for it in input:
            items.append({
                'external_id': it.external_id,
                'posted_at': dt.datetime.fromisoformat(it.posted_at),
                'amount': it.amount,
                'currency': it.currency,
                'description': it.description,
            })
        result = BankTransactionService(session).import_bulk(tenant_id, idempotency_key, items)
        return BankImportResultType(
            imported=result.get('imported', 0),
            deduped=result.get('deduped', 0),
            duplicate_external_ids=result.get('duplicate_external_ids', 0),
            transaction_ids=result.get('transaction_ids', []),
        )
