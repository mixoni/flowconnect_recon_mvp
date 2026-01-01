import datetime as dt

def test_create_invoice(client):
    # create tenant
    t = client.post("/tenants", json={"name": "t1"}).json()
    tid = t["id"]

    inv = client.post(f"/tenants/{tid}/invoices", json={
        "amount": 100.00,
        "currency": "USD",
        "invoice_date": "2025-01-01",
        "description": "Acme invoice"
    }).json()

    assert inv["tenant_id"] == tid
    assert float(inv["amount"]) == 100.0
    assert inv["status"] == "open"

def test_list_invoices_with_filter(client):
    t = client.post("/tenants", json={"name": "t2"}).json()
    tid = t["id"]

    client.post(f"/tenants/{tid}/invoices", json={"amount": 50, "currency":"USD"})
    client.post(f"/tenants/{tid}/invoices", json={"amount": 150, "currency":"USD"})

    # filter range
    res = client.get(f"/tenants/{tid}/invoices?amount_min=100&amount_max=200").json()
    assert len(res) == 1
    assert float(res[0]["amount"]) == 150.0

def test_delete_invoice(client):
    t = client.post("/tenants", json={"name": "t3"}).json()
    tid = t["id"]

    inv = client.post(f"/tenants/{tid}/invoices", json={"amount": 70, "currency":"USD"}).json()
    invoice_id = inv["id"]

    d = client.delete(f"/tenants/{tid}/invoices/{invoice_id}").json()
    assert d["deleted"] is True

    res = client.get(f"/tenants/{tid}/invoices").json()
    assert res == []
