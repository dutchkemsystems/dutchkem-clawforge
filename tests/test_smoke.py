"""Smoke tests for Clawforge API using pytest TestClient."""

import pytest
from fastapi.testclient import TestClient

from clawforge.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "clawforge"


def test_list_tasks(client):
    """Test list tasks endpoint."""
    response = client.get("/v1/tasks")
    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    assert "count" in data


def test_list_tasks_with_filter(client):
    """Test list tasks with status filter."""
    response = client.get("/v1/tasks?status=FUNDED")
    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data


def test_get_task_not_found(client):
    """Test get task that doesn't exist."""
    response = client.get("/v1/tasks/nonexistent")
    assert response.status_code == 404


def test_get_ledger(client):
    """Test get ledger endpoint."""
    response = client.get("/v1/ledger")
    assert response.status_code == 200
    data = response.json()
    assert "entries" in data
    assert "count" in data


def test_get_balance(client):
    """Test get balance endpoint."""
    response = client.get("/v1/ledger/balance")
    assert response.status_code == 200
    data = response.json()
    assert data["currency"] == "USDC"


def test_get_audit_log(client):
    """Test get audit log endpoint."""
    response = client.get("/v1/audit")
    assert response.status_code == 200
    data = response.json()
    assert "entries" in data
    assert "count" in data


def test_verify_audit_chain(client):
    """Test verify audit chain endpoint."""
    response = client.get("/v1/audit/verify")
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True


def test_get_sentinel_status(client):
    """Test get sentinel status endpoint."""
    response = client.get("/v1/sentinel/status")
    assert response.status_code == 200


def test_get_reputation(client):
    """Test get reputation endpoint."""
    response = client.get("/v1/reputation")
    assert response.status_code == 200


def test_get_pending_approvals(client):
    """Test get pending approvals endpoint."""
    response = client.get("/v1/trust/pending-approvals")
    assert response.status_code == 200
    data = response.json()
    assert "approvals" in data


def test_bid_on_task(client):
    """Test bid on task endpoint."""
    response = client.post("/v1/tasks/task-test/bid?bid_amount=50.0")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "task-test"
    assert data["bid_amount"] == 50.0


def test_bid_invalid_amount(client):
    """Test bid with invalid amount."""
    response = client.post("/v1/tasks/task-test/bid?bid_amount=-10.0")
    assert response.status_code == 400


def test_submit_proof(client):
    """Test submit proof endpoint."""
    response = client.post("/v1/tasks/task-test/submit")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "proof_submitted"


def test_reclaim_stake(client):
    """Test reclaim stake endpoint."""
    response = client.post("/v1/tasks/task-test/stake-reclaim")
    assert response.status_code == 200


def test_rate_task(client):
    """Test rate task endpoint."""
    response = client.post("/v1/reputation/rate?task_id=task-test&rating=4.5")
    assert response.status_code == 200
    data = response.json()
    assert data["rating"] == 4.5


def test_rate_invalid_rating(client):
    """Test rate with invalid rating."""
    response = client.post("/v1/reputation/rate?task_id=task-test&rating=6.0")
    assert response.status_code == 400


def test_approve_trust_request_not_found(client):
    """Test approve trust request that doesn't exist."""
    response = client.post("/v1/trust/approve/999")
    assert response.status_code == 404


def test_reject_trust_request_not_found(client):
    """Test reject trust request that doesn't exist."""
    response = client.post("/v1/trust/reject/999")
    assert response.status_code == 404


def test_chained_operations(client):
    """Test chained bid -> submit -> reclaim -> rate operations."""
    # Bid
    response = client.post("/v1/tasks/task-chain/bid?bid_amount=25.0")
    assert response.status_code == 200

    # Submit
    response = client.post("/v1/tasks/task-chain/submit")
    assert response.status_code == 200

    # Reclaim
    response = client.post("/v1/tasks/task-chain/stake-reclaim")
    assert response.status_code == 200

    # Rate
    response = client.post("/v1/reputation/rate?task_id=task-chain&rating=5.0")
    assert response.status_code == 200


def test_get_task_settlement_not_found(client):
    """Test get settlement for non-existent task."""
    response = client.get("/v1/settlement/nonexistent")
    assert response.status_code == 404
