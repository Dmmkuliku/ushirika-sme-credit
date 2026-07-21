from datetime import date, datetime, timedelta, timezone

from tests.conftest import create_admin, create_lender_via_admin, login, register_sme


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("healthy", "degraded")
    assert "version" in data


def test_register_and_login_sme(client):
    user = register_sme(client)
    assert user["login_id"] == "19900101123456789012"
    assert user["role"] == "sme"

    token = login(client, "19900101123456789012")
    assert len(token) > 20


def test_create_lender_via_admin(client, db):
    admin_token = create_admin(client, db)
    resp = client.post(
        "/api/admin/accounts/lender",
        json={
            "membership_number": "EMP099",
            "full_name": "New Lender",
            "gender": "Female",
            "organization": "NMB",
            "work_email": "new@nmb.co.tz",
            "pin": "5678",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "lender"

    token = login(client, "EMP099", "5678")
    assert len(token) > 20


def test_sme_cannot_self_register_as_lender(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "nida": "19850515987654321098",
            "phone": "+255712345678",
            "full_name": "Test SME",
            "location": "Dar",
            "business_type": "Retailer",
            "gender": "Male",
            "date_of_birth": "1985-05-15",
            "tin": "987654321",
            "pin": "1234",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "sme"


def test_role_permissions(client, db):
    register_sme(client, "19900101123456789012")
    lender_token = create_lender_via_admin(client, db, "EMP010")
    sme_token = login(client, "19900101123456789012")

    resp = client.get("/api/lender/portfolio", headers={"Authorization": f"Bearer {sme_token}"})
    assert resp.status_code == 403

    resp = client.get("/api/lender/portfolio", headers={"Authorization": f"Bearer {lender_token}"})
    assert resp.status_code == 200


def test_transactions_and_scoring(client):
    register_sme(client, "19951231456789012345")
    token = login(client, "19951231456789012345")
    headers = {"Authorization": f"Bearer {token}"}

    now = datetime.now(timezone.utc).isoformat()
    for i in range(5):
        resp = client.post(
            "/api/transactions",
            json={
                "transaction_ref": f"REF-{i}",
                "counterparty_tin": f"{100000000 + i}",
                "counterparty_name": f"Partner {i}",
                "counterparty_type": "supplier",
                "order_type": "purchase",
                "amount_tzs": 1_000_000 + i * 100_000,
                "payment_status": "paid",
                "due_date": now,
                "paid_date": now,
                "days_delayed": i,
                "transaction_date": now,
            },
            headers=headers,
        )
        assert resp.status_code == 201

    resp = client.post("/api/credit/score", json={}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert 300 <= data["score"] <= 850
    assert data["eligible_financing_tzs"] >= 0
    assert data["risk_band"] in ("low", "medium", "high")


def test_score_requires_min_transactions(client):
    register_sme(client, "19800101111111111111")
    token = login(client, "19800101111111111111")
    headers = {"Authorization": f"Bearer {token}"}

    now = datetime.now(timezone.utc).isoformat()
    client.post(
        "/api/transactions",
        json={
            "transaction_ref": "REF-ONLY",
            "counterparty_tin": "100000001",
            "counterparty_name": "Partner",
            "counterparty_type": "supplier",
            "order_type": "purchase",
            "amount_tzs": 500_000,
            "payment_status": "paid",
            "due_date": now,
            "transaction_date": now,
        },
        headers=headers,
    )

    resp = client.post("/api/credit/score", json={}, headers=headers)
    assert resp.status_code == 400


def test_invalid_token_rejected(client):
    resp = client.get("/api/sme/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401


def test_pin_validation(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "nida": "12345678901234567890",
            "phone": "+255712345678",
            "full_name": "Test",
            "location": "Dar",
            "business_type": "Retailer",
            "gender": "Male",
            "date_of_birth": "1990-01-01",
            "pin": "123",
        },
    )
    assert resp.status_code == 422


def test_registration_normalizes_tanzanian_phone_and_rejects_under_18(client):
    payload = {
        "nida": "19900101123456789012",
        "phone": "655786630",
        "full_name": "Adult SME",
        "location": "Dar es Salaam",
        "business_type": "Retailer",
        "gender": "Female",
        "nationality": "Tanzanian",
        "date_of_birth": "1990-01-01",
        "tin": "987654321",
        "pin": "1234",
    }
    invalid_nida = dict(payload)
    invalid_nida["nida"] = "1990010112345678901A"
    resp = client.post("/api/auth/register", json=invalid_nida)
    assert resp.status_code == 422
    assert "NIDA must be exactly 20 digits" in resp.text

    mismatched_dob = dict(payload)
    mismatched_dob["date_of_birth"] = "1990-01-02"
    resp = client.post("/api/auth/register", json=mismatched_dob)
    assert resp.status_code == 422
    assert "must match the first 8 NIDA digits" in resp.text

    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 201
    token = login(client, payload["nida"])
    profile = client.get("/api/sme/profile", headers={"Authorization": f"Bearer {token}"}).json()
    assert profile["phone"] == "+255655786630"

    underage = dict(payload)
    underage["tin"] = "987654322"
    underage_dob = date.today() - timedelta(days=17 * 365)
    underage["date_of_birth"] = underage_dob.isoformat()
    underage["nida"] = f"{underage_dob:%Y%m%d}123456789012"
    resp = client.post("/api/auth/register", json=underage)
    assert resp.status_code == 422
    assert "turn 18" in resp.text


def test_future_transaction_date_is_rejected(client):
    register_sme(client, "19951231456789012345")
    token = login(client, "19951231456789012345")
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    resp = client.post(
        "/api/transactions",
        json={
            "transaction_ref": "FUTURE-1",
            "counterparty_tin": "100000001",
            "counterparty_name": "Future Partner",
            "counterparty_type": "buyer",
            "order_type": "sale",
            "amount_tzs": 100000,
            "payment_status": "paid",
            "transaction_date": future,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
    assert "cannot be in the future" in resp.text


def test_admin_account_management(client, db):
    admin_token = create_admin(client, db)
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = client.get("/api/admin/accounts", headers=headers)
    assert resp.status_code == 200

    register_sme(client, "19900101123456789012")
    resp = client.get("/api/admin/accounts?role=sme", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_lender_portfolio_with_nida(client, db):
    register_sme(client, "19900101123456789012")
    lender_token = create_lender_via_admin(client, db, "EMP020")

    resp = client.get("/api/lender/portfolio", headers={"Authorization": f"Bearer {lender_token}"})
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    assert "nida" in items[0]
    assert "full_name" in items[0]


def test_csv_import_scores_without_blocking_training(client, monkeypatch):
    """Import must return quickly; heavy GridSearchCV runs in background only."""
    from app.services import ml_training

    sync_called = {"value": False}

    def _spy_retrain(db_session):
        sync_called["value"] = True
        return None

    scheduled = {"value": False}

    def _spy_schedule():
        scheduled["value"] = True

    monkeypatch.setattr(ml_training, "retrain_after_sme_data_change", _spy_retrain)
    monkeypatch.setattr("app.routers.transactions.schedule_background_retrain", _spy_schedule)

    register_sme(client, "19951231456789012345")
    token = login(client, "19951231456789012345")
    headers = {"Authorization": f"Bearer {token}"}

    csv_content = (
        "transaction_ref,counterparty_tin,counterparty_name,counterparty_type,order_type,"
        "amount_tzs,payment_status,transaction_date\n"
        "TX-A,100123456,Partner A,buyer,sale,250000,paid,2025-01-10\n"
        "TX-B,100234567,Partner B,seller,purchase,180000,paid,2025-01-20\n"
        "TX-C,100345678,Partner C,buyer,sale,320000,paid,2025-02-05\n"
        "TX-D,100456789,Partner D,buyer,sale,150000,paid,2025-02-10\n"
        "TX-E,100567890,Partner E,seller,purchase,210000,paid,2025-03-01\n"
    )
    resp = client.post(
        "/api/transactions/import",
        files={"file": ("sample.csv", csv_content.encode(), "text/csv")},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 5
    assert data.get("model_training_scheduled") is True
    assert sync_called["value"] is False
    assert scheduled["value"] is True
    assert data.get("score_ready") is True
