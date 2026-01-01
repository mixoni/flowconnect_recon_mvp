# Multi-Tenant Invoice Reconciliation API (MVP)

This repo implements a **multi-tenant** invoice reconciliation backend in **Python 3.13** using:

- FastAPI (REST)
- Strawberry GraphQL
- SQLAlchemy 2.0
- SQLite (local)

The goal is to demonstrate senior-level engineering fundamentals: **tenant isolation**, **transaction boundaries**, **idempotent bulk import**, deterministic **reconciliation scoring**, and **pragmatic AI integration** (with graceful fallback).

## Quickstart

### 1) Create venv + install

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install -e ".[dev]"
```

### 2) Run the API

```bash
uvicorn app.main:app --reload
```

- REST docs: http://127.0.0.1:8000/docs
- GraphQL endpoint: http://127.0.0.1:8000/graphql

### 3) Run tests

```bash
pytest
```

## Architecture (Clean boundaries)

- `app/api/*` – thin transport layer (FastAPI + GraphQL routers)
- `app/services/*` – business logic (tenant-scoped), pure Python orchestration
- `app/db/*` – SQLAlchemy models + session management
- `app/schemas/*` – request/response DTOs (Pydantic)

Transport layers call the **same service layer**.

## Multi-tenancy approach

- Every persisted entity (except `tenants`) includes `tenant_id`.
- All service methods require `tenant_id` and enforce it in reads/writes.
- API routes are tenant-scoped via `/tenants/{tenant_id}/...`.

## Idempotent bank import

`POST /tenants/{tenant_id}/bank-transactions/import` requires `Idempotency-Key`.

Implementation:
- Hash of the canonical JSON payload is computed (`sha256` over sorted JSON).
- First request stores `(tenant_id, key, request_hash, response_json)`.
- Replays:
  - same key + same payload hash → returns the stored response
  - same key + different payload hash → `409 Conflict`

## Reconciliation scoring (deterministic)

A simple score (0–100) is computed per invoice/transaction:

- Exact amount match: +60
- Date proximity within ±3 days: +0..25 (linear decay)
- Text overlap heuristic: +0..15
- Currency mismatch: candidate excluded

Candidates are ranked deterministically by:
1) score desc  
2) abs(date_diff) asc  
3) transaction id asc

Reconcile persists `matches` with `status="proposed"` for the top N candidates per invoice.

Confirming a match:
- sets match status to `confirmed`
- marks invoice as `matched`
- ensures only one confirmed match per invoice (enforced in service)

## AI explanation (pragmatic)

`GET /tenants/{tenant_id}/reconcile/explain?invoice_id=...&transaction_id=...`

- If an API key is present (`AI_API_KEY`), a **stub client** returns a short explanation.
- If AI is unavailable / errors / missing key → deterministic fallback explanation based on the same features used in scoring.

The AI client is designed to be easily mocked in tests.

## Deliberate scope tradeoffs (MVP)

- Vendors are omitted to keep focus on core coordination mechanics.
- GraphQL implements a minimal surface area, but uses the same services.
- No migrations (tables are created on startup in local mode). In production, Alembic would be used.


## Project structure (feature modules)

This repo is organized in **feature modules** (similar to NestJS/.NET vertical slices):

- `app/modules/tenants/` — tenant CRUD (REST + GraphQL + service + schemas)
- `app/modules/invoices/` — invoices (REST + GraphQL + service + schemas)
- `app/modules/transactions/` — idempotent bank transaction import (REST + GraphQL + service + schemas)
- `app/modules/reconciliation/` — reconciliation + confirm + AI explanation (REST + GraphQL + service + schemas)

Shared infrastructure:

- `app/db/` — SQLAlchemy models/session/init
- `app/core/` — settings + domain errors
- `app/api/` — thin aggregators that compose module routers/schema
