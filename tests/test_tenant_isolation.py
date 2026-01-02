"""
Test multi-tenant isolation: ensure tenant A cannot see tenant B's data.
"""

def test_invoice_tenant_isolation(client):
    """Tenant A should not see invoices from Tenant B"""
    # Create two tenants
    t1 = client.post("/tenants", json={"name": "TenantA"}).json()
    t2 = client.post("/tenants", json={"name": "TenantB"}).json()

    tenant_a_id = t1["id"]
    tenant_b_id = t2["id"]

    # Create invoices for Tenant A
    client.post(f"/tenants/{tenant_a_id}/invoices", json={
        "amount": 100.0,
        "currency": "USD",
        "description": "Tenant A Invoice"
    })
    client.post(f"/tenants/{tenant_a_id}/invoices", json={
        "amount": 200.0,
        "currency": "USD",
        "description": "Tenant A Invoice 2"
    })

    # Create invoice for Tenant B
    client.post(f"/tenants/{tenant_b_id}/invoices", json={
        "amount": 300.0,
        "currency": "USD",
        "description": "Tenant B Invoice"
    })

    # Tenant A should only see 2 invoices
    tenant_a_invoices = client.get(f"/tenants/{tenant_a_id}/invoices").json()
    assert len(tenant_a_invoices) == 2
    assert all(inv["tenant_id"] == tenant_a_id for inv in tenant_a_invoices)

    # Tenant B should only see 1 invoice
    tenant_b_invoices = client.get(f"/tenants/{tenant_b_id}/invoices").json()
    assert len(tenant_b_invoices) == 1
    assert tenant_b_invoices[0]["tenant_id"] == tenant_b_id
    assert tenant_b_invoices[0]["description"] == "Tenant B Invoice"


def test_bank_transaction_tenant_isolation(client):
    """Tenant A should not access Tenant B's bank transactions via reconciliation"""
    # Create two tenants
    t1 = client.post("/tenants", json={"name": "TenantC"}).json()
    t2 = client.post("/tenants", json={"name": "TenantD"}).json()

    tenant_c_id = t1["id"]
    tenant_d_id = t2["id"]

    # Import transactions for Tenant C
    client.post(
        f"/tenants/{tenant_c_id}/bank-transactions/import",
        json=[{
            "external_id": "c1",
            "posted_at": "2025-01-05T10:00:00Z",
            "amount": 100.0,
            "currency": "USD",
            "description": "Tenant C payment"
        }],
        headers={"Idempotency-Key": "tenant-c-key"}
    )

    # Import transactions for Tenant D
    client.post(
        f"/tenants/{tenant_d_id}/bank-transactions/import",
        json=[{
            "external_id": "d1",
            "posted_at": "2025-01-05T10:00:00Z",
            "amount": 200.0,
            "currency": "USD",
            "description": "Tenant D payment"
        }],
        headers={"Idempotency-Key": "tenant-d-key"}
    )

    # Create invoice for Tenant C
    inv_c = client.post(f"/tenants/{tenant_c_id}/invoices", json={
        "amount": 100.0,
        "currency": "USD",
        "invoice_date": "2025-01-05",
        "description": "Tenant C invoice"
    }).json()

    # Reconcile for Tenant C - should only match C's transactions
    matches_c = client.post(f"/tenants/{tenant_c_id}/reconcile", json={
        "window_days": 5,
        "max_candidates_per_invoice": 5
    }).json()

    # Should have matches only with Tenant C's transactions
    assert len(matches_c) > 0
    for match in matches_c:
        assert match["tenant_id"] == tenant_c_id
        # Bank transaction IDs should not cross tenant boundaries
        # Verify the match is for tenant C's invoice
        assert match["invoice_id"] == inv_c["id"]


def test_match_confirm_cross_tenant_blocked(client):
    """Tenant A should not be able to confirm Tenant B's matches"""
    # Create two tenants
    t1 = client.post("/tenants", json={"name": "TenantE"}).json()
    t2 = client.post("/tenants", json={"name": "TenantF"}).json()

    tenant_e_id = t1["id"]
    tenant_f_id = t2["id"]

    # Create invoice for Tenant E
    inv_e = client.post(f"/tenants/{tenant_e_id}/invoices", json={
        "amount": 150.0,
        "currency": "USD",
        "invoice_date": "2025-01-06",
        "description": "Tenant E invoice"
    }).json()

    # Import transaction for Tenant E
    client.post(
        f"/tenants/{tenant_e_id}/bank-transactions/import",
        json=[{
            "external_id": "e1",
            "posted_at": "2025-01-06T10:00:00Z",
            "amount": 150.0,
            "currency": "USD",
            "description": "Tenant E payment"
        }],
        headers={"Idempotency-Key": "tenant-e-key"}
    )

    # Reconcile for Tenant E
    matches_e = client.post(f"/tenants/{tenant_e_id}/reconcile", json={
        "window_days": 5,
        "max_candidates_per_invoice": 5
    }).json()

    assert len(matches_e) > 0
    match_id = matches_e[0]["id"]

    # Tenant F tries to confirm Tenant E's match - should fail (404 or similar)
    response = client.post(f"/tenants/{tenant_f_id}/matches/{match_id}/confirm")
    assert response.status_code == 404  # Match not found for tenant F


def test_invoice_delete_cross_tenant_blocked(client):
    """Tenant A should not be able to delete Tenant B's invoices"""
    # Create two tenants
    t1 = client.post("/tenants", json={"name": "TenantG"}).json()
    t2 = client.post("/tenants", json={"name": "TenantH"}).json()

    tenant_g_id = t1["id"]
    tenant_h_id = t2["id"]

    # Create invoice for Tenant G
    inv_g = client.post(f"/tenants/{tenant_g_id}/invoices", json={
        "amount": 500.0,
        "currency": "USD",
        "description": "Tenant G invoice"
    }).json()

    invoice_g_id = inv_g["id"]

    # Tenant H tries to delete Tenant G's invoice - should fail (404)
    response = client.delete(f"/tenants/{tenant_h_id}/invoices/{invoice_g_id}")
    assert response.status_code == 404

    # Verify Tenant G's invoice still exists
    invoices_g = client.get(f"/tenants/{tenant_g_id}/invoices").json()
    assert len(invoices_g) == 1
    assert invoices_g[0]["id"] == invoice_g_id