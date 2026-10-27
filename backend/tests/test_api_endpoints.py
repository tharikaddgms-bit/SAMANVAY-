import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.seed_data import seed_database

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    seed_database(reset=True)

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["mode"] == "DEMO_MODE"

def test_auth_login():
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "INSTITUTION_ADMIN"

def test_dashboard_stats():
    response = client.get("/api/dashboard/stats", headers={"X-Demo-User": "admin"})
    assert response.status_code == 200
    data = response.json()
    assert data["metrics"]["total_student_records"] >= 15
    assert data["verification_breakdown"]["OFFICIALLY_VERIFIED"] == 0
    assert data["demo_mode"]["is_active"] is True

def test_student_list_and_rbac():
    # Admin gets full cohort
    admin_resp = client.get("/api/students", headers={"X-Demo-User": "admin"})
    assert admin_resp.status_code == 200
    assert admin_resp.json()["total"] >= 15

    # Student only gets their own record
    student_resp = client.get("/api/students", headers={"X-Demo-User": "student"})
    assert student_resp.status_code == 200
    assert student_resp.json()["total"] == 1
    assert student_resp.json()["is_student_scoped"] is True

def test_discrepancy_review_action():
    # Fetch discrepancies
    disc_resp = client.get("/api/reconciliation/discrepancies", headers={"X-Demo-User": "admin"})
    assert disc_resp.status_code == 200
    items = disc_resp.json()["items"]
    assert len(items) > 0

    target = items[0]
    # Review with ACCEPT_CORRECTION
    rev_resp = client.post(
        f"/api/reconciliation/discrepancies/{target['id']}/review",
        json={"decision": "ACCEPT_CORRECTION", "notes": "Approved by verification officer during demo test."},
        headers={"X-Demo-User": "officer"},
    )
    assert rev_resp.status_code == 200
    assert rev_resp.json()["decision"] == "ACCEPT_CORRECTION"

def test_credential_verification_public():
    # Get Vikram's revoked credential
    client.post("/api/demo/reset", headers={"X-Demo-User": "admin"})
    vikram_cred = client.get("/api/credentials/detail/CRED-DEMO-", headers={"X-Demo-User": "admin"})
    # Query student 11 credentials
    s11 = client.get("/api/credentials/student/11", headers={"X-Demo-User": "admin"}).json()
    assert len(s11) > 0
    cid = s11[0]["credential_id"]

    # Verify via public endpoint
    verify_resp = client.post("/api/credentials/verify", json={"credential_id": cid})
    assert verify_resp.status_code == 200
    res = verify_resp.json()
    assert res["status"] == "REVOKED"
    assert res["is_revoked"] is True
