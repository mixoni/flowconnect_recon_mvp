from __future__ import annotations
import json, hashlib
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models import BankTransaction, IdempotencyKey
from app.core.errors import ConflictError, BadRequestError

def _canonical_hash(payload) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

class BankTransactionService:
    def __init__(self, session: Session):
        self.session = session

    def import_bulk(self, tenant_id: int, idempotency_key: str, items: list[dict]) -> dict:
        req_hash = _canonical_hash(items)

        existing = self.session.scalars(
            select(IdempotencyKey).where(IdempotencyKey.tenant_id == tenant_id, IdempotencyKey.key == idempotency_key)
        ).first()

        if existing:
            if existing.request_hash != req_hash:
                raise ConflictError("Idempotency-Key reused with different payload")
            return json.loads(existing.response_json)

        if not items:
            raise BadRequestError("Items list must not be empty")

        imported = 0
        duplicate_external_ids = 0
        transaction_ids: list[int] = []

        required = ("posted_at", "amount", "description")

        try:
            for it in items:
                for k in required:
                    if k not in it or it[k] is None:
                        raise BadRequestError(f"Missing required field: {k}")

                ext_id = it.get("external_id")
                if ext_id:
                    dup = self.session.scalars(
                        select(BankTransaction).where(
                            BankTransaction.tenant_id == tenant_id,
                            BankTransaction.external_id == ext_id,
                        )
                    ).first()
                    if dup:
                        duplicate_external_ids += 1
                        continue

                tx = BankTransaction(
                    tenant_id=tenant_id,
                    external_id=ext_id,
                    posted_at=it["posted_at"],
                    amount=it["amount"],
                    currency=it.get("currency", "USD"),
                    description=it["description"],
                )
                self.session.add(tx)
                self.session.flush()
                transaction_ids.append(tx.id)
                imported += 1

            result = {
                "imported": imported,
                "deduped": duplicate_external_ids,
                "duplicate_external_ids": duplicate_external_ids,
                "transaction_ids": transaction_ids,
            }

            idem = IdempotencyKey(
                tenant_id=tenant_id,
                key=idempotency_key,
                request_hash=req_hash,
                response_json=json.dumps(result),
            )
            self.session.add(idem)

            self.session.commit()
            return result
        except Exception:
            self.session.rollback()
            raise
