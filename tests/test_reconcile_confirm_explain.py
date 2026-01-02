def test_reconcile_ranking_and_confirm(client, monkeypatch):
    t = client.post("/tenants", json={"name": "t6"}).json()
    tid = t["id"]

    inv = client.post(f"/tenants/{tid}/invoices", json={
        "amount": 100.00,
        "currency": "USD",
        "invoice_date": "2025-01-01",
        "description": "Acme January"
    }).json()
    invoice_id = inv["id"]

    payload = [
        {"external_id": "a", "posted_at": "2025-01-10T10:00:00Z", "amount": 100.00, "currency": "USD", "description": "Random"},
        {"external_id": "b", "posted_at": "2025-01-02T10:00:00Z", "amount": 100.00, "currency": "USD", "description": "Acme January payment"},
        {"external_id": "c", "posted_at": "2025-01-02T10:00:00Z", "amount": 90.00,  "currency": "USD", "description": "Acme January payment"},
    ]

    import_res = client.post(
        f"/tenants/{tid}/bank-transactions/import",
        json=payload,
        headers={"Idempotency-Key": "k3"},
    ).json()

    # id-ovi su deterministični po insert redosledu (payload redosled)
    tx_id_a, tx_id_b, tx_id_c = import_res["transaction_ids"]

    matches = client.post(
        f"/tenants/{tid}/reconcile",
        json={"window_days": 3, "max_candidates_per_invoice": 2},
    ).json()

    assert len(matches) >= 1
    top = matches[0]
    assert top["invoice_id"] == invoice_id
    assert top["bank_transaction_id"] == tx_id_b

    confirmed = client.post(f"/tenants/{tid}/matches/{top['id']}/confirm").json()
    assert confirmed["status"] == "confirmed"

    ex = client.get(
        f"/tenants/{tid}/reconcile/explain?invoice_id={invoice_id}&transaction_id={top['bank_transaction_id']}"
    ).json()
    assert ex["explanation"]  # non-empty fallback or AI explanation
