import os
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

os.environ.setdefault("CLAW_EARN_WALLET", "0x0000000000000000000000000000000000000000")
os.environ.setdefault("CLAW_EARN_PRIVATE_KEY", "0x" + "1" * 64)

import asyncio
from clawforge.protocol.trust import TrustBoundary, TrustBoundaryError


class TestTrustBoundaryValidation:
    def test_valid_https_url(self):
        tb = TrustBoundary()
        assert tb.validate_url("https://aiagentstore.ai/claw/tasks") is True

    def test_valid_https_subdomain(self):
        tb = TrustBoundary()
        assert tb.validate_url("https://api.aiagentstore.ai/claw-earn.json") is True

    def test_rejects_http_url(self):
        tb = TrustBoundary()
        with pytest.raises(TrustBoundaryError, match="Non-HTTPS"):
            tb.validate_url("http://aiagentstore.ai/claw/tasks")

    def test_rejects_ftp_url(self):
        tb = TrustBoundary()
        with pytest.raises(TrustBoundaryError, match="Non-HTTPS"):
            tb.validate_url("ftp://aiagentstore.ai/claw/tasks")

    def test_rejects_untrusted_host(self):
        tb = TrustBoundary()
        with patch.object(tb, "_request_human_approval"):
            with pytest.raises(TrustBoundaryError, match="Untrusted host"):
                tb.validate_url("https://evil.com/claw/tasks")

    def test_rejects_empty_string(self):
        tb = TrustBoundary()
        with pytest.raises(TrustBoundaryError):
            tb.validate_url("")

    def test_rejects_localhost(self):
        tb = TrustBoundary()
        with patch.object(tb, "_request_human_approval"):
            with pytest.raises(TrustBoundaryError, match="Untrusted host"):
                tb.validate_url("https://localhost:8000/claw/tasks")

    def test_untrusted_host_queues_approval(self):
        tb = TrustBoundary()
        with patch.object(tb, "_request_human_approval") as mock_approve:
            with pytest.raises(TrustBoundaryError):
                tb.validate_url("https://evil.com/phish")
            mock_approve.assert_called_once_with("https://evil.com/phish", "untrusted_host")

    def test_request_human_approval_adds_to_queue(self):
        tb = TrustBoundary()
        with patch.object(tb, "_request_human_approval") as mock_approval:
            tb._approval_queue.append({
                "url": "https://evil.com/x",
                "reason": "untrusted_host",
                "timestamp": 0.0,
                "status": "pending",
            })
        pending = tb.get_pending_approvals()
        assert len(pending) == 1
        assert pending[0]["reason"] == "untrusted_host"
        assert pending[0]["status"] == "pending"

    def test_approve_request(self):
        tb = TrustBoundary()
        tb._approval_queue.append({
            "url": "https://evil.com/x",
            "reason": "untrusted_host",
            "timestamp": 0.0,
            "status": "pending",
        })
        assert tb.approve_request(0) is True
        assert tb.get_pending_approvals() == []

    def test_reject_request(self):
        tb = TrustBoundary()
        tb._approval_queue.append({
            "url": "https://evil.com/x",
            "reason": "untrusted_host",
            "timestamp": 0.0,
            "status": "pending",
        })
        assert tb.reject_request(0) is True
        assert len(tb.get_pending_approvals()) == 0

    def test_approve_invalid_index(self):
        tb = TrustBoundary()
        assert tb.approve_request(99) is False

    def test_reject_invalid_index(self):
        tb = TrustBoundary()
        assert tb.reject_request(99) is False

    def test_approve_already_approved(self):
        tb = TrustBoundary()
        tb._approval_queue.append({
            "url": "url", "reason": "reason", "timestamp": 0.0, "status": "approved",
        })
        assert tb.approve_request(0) is False

    def test_reject_already_rejected(self):
        tb = TrustBoundary()
        tb._approval_queue.append({
            "url": "url", "reason": "reason", "timestamp": 0.0, "status": "rejected",
        })
        assert tb.reject_request(0) is False

    def test_multiple_approvals(self):
        tb = TrustBoundary()
        for i in range(3):
            tb._approval_queue.append({
                "url": f"url{i}", "reason": f"r{i}", "timestamp": 0.0, "status": "pending",
            })
        assert len(tb.get_pending_approvals()) == 3
        tb.approve_request(0)
        assert len(tb.get_pending_approvals()) == 2


class TestTrustBoundaryRedirects:
    @pytest.mark.asyncio
    async def test_redirect_to_untrusted_host_blocked(self):
        tb = TrustBoundary()
        mock_response = MagicMock()
        mock_response.url = "https://evil.com/redirected"
        mock_response.history = [MagicMock()]

        mock_client = AsyncMock()
        mock_client.head = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("clawforge.protocol.trust.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(TrustBoundaryError, match="Redirect to untrusted host"):
                await tb.check_redirects("https://aiagentstore.ai/redirect-test")

    @pytest.mark.asyncio
    async def test_redirect_within_trust_boundary(self):
        tb = TrustBoundary()
        mock_response = MagicMock()
        mock_response.url = "https://aiagentstore.ai/destination"
        mock_response.history = [MagicMock()]

        mock_client = AsyncMock()
        mock_client.head = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("clawforge.protocol.trust.httpx.AsyncClient", return_value=mock_client):
            result = await tb.check_redirects("https://aiagentstore.ai/start")
            assert "aiagentstore.ai" in result


from clawforge.protocol.loader import ProtocolLoader


class TestProtocolLoader:
    def _make_loader(self, tmpdir):
        with patch("clawforge.protocol.loader.get_settings") as mock_settings:
            mock_s = MagicMock()
            mock_s.get_protocol_path.return_value = Path(tmpdir) / "protocol"
            mock_s.CLAW_EARN_BASE_URL = "https://aiagentstore.ai"
            mock_settings.return_value = mock_s
            loader = ProtocolLoader()
        return loader

    def test_validate_spec_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = self._make_loader(tmpdir)
            spec = {
                "version": "1.0",
                "endpoints": {"tasks": "/claw/tasks", "proof": "/claw/proof", "settlement": "/claw/settle"},
                "schemas": {"task": {}},
            }
            assert loader.validate_spec(spec) is True

    def test_validate_spec_missing_version(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = self._make_loader(tmpdir)
            spec = {"endpoints": {"tasks": "/claw/tasks", "proof": "/claw/proof", "settlement": "/claw/settle"}, "schemas": {}}
            assert loader.validate_spec(spec) is False

    def test_validate_spec_missing_endpoints(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = self._make_loader(tmpdir)
            spec = {"version": "1.0", "endpoints": {"tasks": "/claw/tasks"}, "schemas": {}}
            assert loader.validate_spec(spec) is False

    def test_load_from_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = self._make_loader(tmpdir)
            protocol_path = Path(tmpdir) / "protocol"
            protocol_path.mkdir(parents=True, exist_ok=True)
            spec = {"version": "1.0", "endpoints": {}, "schemas": {}}
            (protocol_path / "claw-earn.json").write_text(json.dumps(spec))
            result = loader._load_from_cache()
            assert result["version"] == "1.0"

    def test_load_from_cache_no_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = self._make_loader(tmpdir)
            with pytest.raises(FileNotFoundError):
                loader._load_from_cache()

    def test_get_version_returns_none_when_no_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = self._make_loader(tmpdir)
            assert loader.get_version() is None

    def test_save_and_load_cache_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = self._make_loader(tmpdir)
            spec = {"version": "2.0", "endpoints": {}, "schemas": {}}
            loader._save_to_cache(spec, "abc123hash")
            result = loader._load_from_cache()
            assert result == spec
            assert loader.get_version() == "abc123hash"

    @pytest.mark.asyncio
    async def test_load_protocol_fallback_to_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = self._make_loader(tmpdir)
            protocol_path = Path(tmpdir) / "protocol"
            protocol_path.mkdir(parents=True, exist_ok=True)
            cached = {"version": "cached", "endpoints": {}, "schemas": {}}
            (protocol_path / "claw-earn.json").write_text(json.dumps(cached))

            with patch.object(loader, "fetch_protocol", side_effect=Exception("network error")):
                result = await loader.load_protocol()
                assert result["version"] == "cached"

    def test_get_endpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = self._make_loader(tmpdir)
            protocol_path = Path(tmpdir) / "protocol"
            protocol_path.mkdir(parents=True, exist_ok=True)
            spec = {"version": "1", "endpoints": {"tasks": "/claw/tasks"}, "schemas": {}}
            (protocol_path / "claw-earn.json").write_text(json.dumps(spec))
            loader._cached_spec = spec
            assert loader.get_endpoint("tasks") == "/claw/tasks"
            assert loader.get_endpoint("nonexistent") is None

    @pytest.mark.asyncio
    async def test_fetch_protocol_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = self._make_loader(tmpdir)
            mock_response = MagicMock()
            mock_response.json.return_value = {"version": "1", "endpoints": {}, "schemas": {}}
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            with patch("clawforge.protocol.loader.httpx.AsyncClient", return_value=mock_client):
                result = await loader.fetch_protocol()
                assert result["version"] == "1"

    def test_validate_spec_version_logged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = self._make_loader(tmpdir)
            spec = {
                "version": "3.0",
                "endpoints": {"tasks": "/t", "proof": "/p", "settlement": "/s"},
                "schemas": {},
            }
            assert loader.validate_spec(spec) is True

    def test_save_backup_existing_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = self._make_loader(tmpdir)
            protocol_path = Path(tmpdir) / "protocol"
            protocol_path.mkdir(parents=True, exist_ok=True)
            spec1 = {"version": "1", "endpoints": {}, "schemas": {}}
            (protocol_path / "claw-earn.json").write_text(json.dumps(spec1))
            spec2 = {"version": "2", "endpoints": {}, "schemas": {}}
            loader._save_to_cache(spec2, "v2hash")
            assert (protocol_path / "claw-earn.json.bak").exists()
            result = loader._load_from_cache()
            assert result["version"] == "2"

    def test_get_endpoint_caches_spec(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = self._make_loader(tmpdir)
            protocol_path = Path(tmpdir) / "protocol"
            protocol_path.mkdir(parents=True, exist_ok=True)
            spec = {"version": "1", "endpoints": {"tasks": "/t"}, "schemas": {}}
            (protocol_path / "claw-earn.json").write_text(json.dumps(spec))
            assert loader.get_endpoint("tasks") == "/t"
            assert loader._cached_spec is not None
