import datetime as dt

def test_import_idempotency_replay(client):
    t = client.post("/tenants", json={"name": "t4"}).json()
    tid = t["id"]

    payload = [{
        "external_id": "ext-1",
        "posted_at": "2025-01-03T10:00:00Z",
        "amount": 100.00,
        "currency": "USD",
        "description": "Payment ACME"
    }]

    headers = {"Idempotency-Key": "k1"}
    r1 = client.post(f"/tenants/{tid}/bank-transactions/import", json=payload, headers=headers).json()
    r2 = client.post(f"/tenants/{tid}/bank-transactions/import", json=payload, headers=headers).json()

    assert r1 == r2
    assert r1["imported"] == 1
    assert r1["deduped"] == 0

def test_import_idempotency_conflict(client):
    t = client.post("/tenants", json={"name": "t5"}).json()
    tid = t["id"]

    payload1 = [{
        "external_id": "ext-1",
        "posted_at": "2025-01-03T10:00:00Z",
        "amount": 100.00,
        "currency": "USD",
        "description": "Payment ACME"
    }]
    payload2 = [{
        "external_id": "ext-1",
        "posted_at": "2025-01-03T10:00:00Z",
        "amount": 101.00,
        "currency": "USD",
        "description": "Payment ACME"
    }]

    headers = {"Idempotency-Key": "k2"}
    client.post(f"/tenants/{tid}/bank-transactions/import", json=payload1, headers=headers)

    r = client.post(f"/tenants/{tid}/bank-transactions/import", json=payload2, headers=headers)
    assert r.status_code == 409
