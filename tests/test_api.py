"""Tests for Clawforge API routes."""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from clawforge.config import get_settings
get_settings.cache_clear()

from clawforge.main import app


@pytest.fixture
def client():
    with tempfile.TemporaryDirectory() as tmpdir:
        tp = Path(tmpdir)
        with patch("clawforge.api.routes.get_settings") as mock_settings:
            mock_s = MagicMock()
            mock_s.ECONOMY_PATH = str(tp / "economy")
            mock_s.AUDIT_PATH = str(tp / "audit")
            mock_s.TASKS_PATH = str(tp / "tasks")
            mock_s.SENTINEL_PATH = str(tp / "sentinel")
            mock_s.MEMORY_PATH = str(tp / "memory")
            mock_s.REPUTATION_PATH = str(tp / "reputation")
            mock_s.CREDENTIALS_PATH = str(tp / "credentials")
            mock_s.PROTOCOL_PATH = str(tp / "protocol")
            mock_s.get_economy_path.return_value = tp / "economy"
            mock_s.get_audit_path.return_value = tp / "audit"
            mock_s.get_tasks_path.return_value = tp / "tasks"
            mock_s.get_sentinel_path.return_value = tp / "sentinel"
            mock_s.get_memory_path.return_value = tp / "memory"
            mock_s.get_protocol_path.return_value = tp / "protocol"
            mock_s.get_config_path.return_value = tp / "config"
            mock_s.get_credentials_path.return_value = tp / "credentials"
            mock_s.SENTINEL_HEARTBEAT_INTERVAL = 60
            mock_s.SENTINEL_FRESHNESS_THRESHOLD = 90
            mock_s.SENTINEL_DEAD_MAN_SWITCH = 300
            mock_s.API_KEY = ""
            mock_s.AUTO_STAKE_PERCENTAGE = 0.10
            mock_s.MAX_DAILY_STAKE_USDC = 1000.0
            mock_settings.return_value = mock_s

            # Reset module-level singletons
            import clawforge.api.routes as routes_mod
            routes_mod._ledger = None
            routes_mod._staker = None
            routes_mod._reputation = None
            routes_mod._hot = None

            # Patch sentinel and trust_boundary singletons
            with patch("clawforge.api.routes.sentinel") as mock_sentinel:
                mock_sentinel.get_status.return_value = {
                    "is_running": False,
                    "restart_count": 0,
                    "uptime_seconds": 0,
                    "dead_mans_switch_active": False,
                }
                with patch("clawforge.api.routes.trust_boundary") as mock_tb:
                    mock_tb.get_pending_approvals.return_value = []
                    mock_tb.approve_request.return_value = False
                    mock_tb.reject_request.return_value = False
                    yield TestClient(app)


class TestHealthCheck:
    def test_health_returns_ok(self, client):
        resp = client.get("/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "clawforge"
        assert "timestamp" in data


class TestTasksEndpoints:
    def test_list_tasks_returns_empty(self, client):
        resp = client.get("/v1/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tasks"] == []
        assert data["count"] == 0

    def test_list_tasks_with_status_filter(self, client):
        resp = client.get("/v1/tasks", params={"status": "FUNDED"})
        assert resp.status_code == 200
        data = resp.json()
        assert "tasks" in data

    def test_get_task_not_found(self, client):
        resp = client.get("/v1/tasks/nonexistent")
        assert resp.status_code == 404

    def test_bid_on_task(self, client):
        resp = client.post("/v1/tasks/task-1/bid", params={"bid_amount": 50.0})
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "task-1"
        assert data["bid_amount"] == 50.0
        assert data["status"] == "submitted"
        assert "stake_amount" in data

    def test_bid_negative_amount_fails(self, client):
        resp = client.post("/v1/tasks/task-1/bid", params={"bid_amount": -10.0})
        assert resp.status_code == 400

    def test_submit_proof(self, client):
        resp = client.post("/v1/tasks/task-1/submit")
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "task-1"
        assert data["status"] == "proof_submitted"

    def test_reclaim_stake(self, client):
        resp = client.post("/v1/tasks/task-1/stake-reclaim")
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "task-1"
        assert "reclaimed_amount" in data


class TestLedgerEndpoints:
    def test_get_ledger(self, client):
        resp = client.get("/v1/ledger")
        assert resp.status_code == 200
        data = resp.json()
        assert "entries" in data
        assert "count" in data

    def test_get_ledger_with_task_filter(self, client):
        resp = client.get("/v1/ledger", params={"task_id": "task-1"})
        assert resp.status_code == 200

    def test_get_balance(self, client):
        resp = client.get("/v1/ledger/balance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["balance"] == 0.0
        assert data["currency"] == "USDC"
        assert "staked" in data


class TestAuditEndpoints:
    def test_get_audit_log(self, client):
        resp = client.get("/v1/audit")
        assert resp.status_code == 200
        data = resp.json()
        assert "entries" in data

    def test_get_audit_log_with_filters(self, client):
        resp = client.get("/v1/audit", params={"task_id": "t1", "since": 1000.0})
        assert resp.status_code == 200

    def test_verify_audit_chain(self, client):
        resp = client.get("/v1/audit/verify")
        assert resp.status_code == 200
        assert resp.json()["valid"] is True


class TestSettlementEndpoint:
    def test_get_settlement_not_found(self, client):
        resp = client.get("/v1/settlement/nonexistent-task")
        assert resp.status_code == 404


class TestSentinelEndpoint:
    def test_sentinel_status(self, client):
        resp = client.get("/v1/sentinel/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "is_running" in data
        assert "restart_count" in data
        assert "uptime_seconds" in data


class TestReputationEndpoint:
    def test_get_reputation(self, client):
        resp = client.get("/v1/reputation")
        assert resp.status_code == 200
        data = resp.json()
        assert "tier" in data
        assert "average_rating" in data
        assert "total_ratings" in data

    def test_rate_task(self, client):
        resp = client.post("/v1/reputation/rate", params={"task_id": "task-1", "rating": 4.5})
        assert resp.status_code == 200
        data = resp.json()
        assert data["rating"] == 4.5
        assert "new_tier" in data

    def test_rate_task_invalid_rating(self, client):
        resp = client.post("/v1/reputation/rate", params={"task_id": "task-1", "rating": 6.0})
        assert resp.status_code == 400


class TestTrustEndpoints:
    def test_get_pending_approvals(self, client):
        resp = client.get("/v1/trust/pending-approvals")
        assert resp.status_code == 200
        assert "approvals" in resp.json()

    def test_approve_nonexistent(self, client):
        resp = client.post("/v1/trust/approve/999")
        assert resp.status_code == 404

    def test_reject_nonexistent(self, client):
        resp = client.post("/v1/trust/reject/999")
        assert resp.status_code == 404
