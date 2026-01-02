from __future__ import annotations
import datetime as dt
import strawberry
from sqlalchemy.orm import Session

from app.modules.transactions.service import BankTransactionService

@strawberry.type
class BankTransactionType:
    id: int
    tenant_id: int
    external_id: str | None
    posted_at: str
    amount: float
    currency: str
    description: str

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
class TransactionsQuery:
    @strawberry.field
    def bank_transactions(
        self,
        info,
        tenant_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> list[BankTransactionType]:
        session: Session = info.context["session"]
        transactions = BankTransactionService(session).list(tenant_id, limit=limit, offset=offset)
        return [
            BankTransactionType(
                id=tx.id,
                tenant_id=tx.tenant_id,
                external_id=tx.external_id,
                posted_at=tx.posted_at.isoformat(),
                amount=float(tx.amount),
                currency=tx.currency,
                description=tx.description,
            )
            for tx in transactions
        ]


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
