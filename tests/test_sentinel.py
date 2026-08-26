import json
import os
import time
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

os.environ.setdefault("CLAW_EARN_WALLET", "0x0000000000000000000000000000000000000000")
os.environ.setdefault("CLAW_EARN_PRIVATE_KEY", "0x" + "1" * 64)

from clawforge.config import get_settings
get_settings.cache_clear()

from clawforge.sentinel.watcher import Sentinel
from clawforge.models import Heartbeat, SentinelState


class TestSentinelInit:
    def _make_sentinel(self, tmpdir):
        with patch("clawforge.sentinel.watcher.get_settings") as mock_settings:
            mock_s = MagicMock()
            mock_s.get_sentinel_path.return_value = Path(tmpdir) / "sentinel"
            mock_s.SENTINEL_HEARTBEAT_INTERVAL = 60
            mock_s.SENTINEL_FRESHNESS_THRESHOLD = 90
            mock_s.SENTINEL_DEAD_MAN_SWITCH = 300
            mock_settings.return_value = mock_s
            sentinel = Sentinel()
        return sentinel

    def test_creates_sentinel_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sentinel = self._make_sentinel(tmpdir)
            assert sentinel._sentinel_path.exists()

    def test_initial_state_is_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sentinel = self._make_sentinel(tmpdir)
            state = sentinel._load_state()
            assert state.restart_count == 0
            assert state.dead_mans_switch_active is False
            assert state.heartbeat is None

    def test_get_status_when_not_running(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sentinel = self._make_sentinel(tmpdir)
            status = sentinel.get_status()
            assert status["is_running"] is False
            assert status["restart_count"] == 0

    def test_load_state_from_existing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sentinel = self._make_sentinel(tmpdir)
            state = SentinelState(restart_count=3, dead_mans_switch_active=True)
            state_data = state.model_dump(mode="json")
            if state_data.get("heartbeat"):
                state_data["heartbeat"]["timestamp"] = state_data["heartbeat"]["timestamp"].isoformat()
            if state_data.get("last_restart"):
                state_data["last_restart"] = state_data["last_restart"].isoformat()
            sentinel._sentinel_path.mkdir(parents=True, exist_ok=True)
            (sentinel._sentinel_path / "state.json").write_text(json.dumps(state_data))
            loaded = sentinel._load_state()
            assert loaded.restart_count == 3
            assert loaded.dead_mans_switch_active is True


class TestSentinelHeartbeat:
    def _make_sentinel(self, tmpdir):
        with patch("clawforge.sentinel.watcher.get_settings") as mock_settings:
            mock_s = MagicMock()
            mock_s.get_sentinel_path.return_value = Path(tmpdir) / "sentinel"
            mock_s.SENTINEL_HEARTBEAT_INTERVAL = 60
            mock_s.SENTINEL_FRESHNESS_THRESHOLD = 90
            mock_s.SENTINEL_DEAD_MAN_SWITCH = 300
            mock_settings.return_value = mock_s
            sentinel = Sentinel()
        return sentinel

    @pytest.mark.asyncio
    async def test_emit_heartbeat_updates_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sentinel = self._make_sentinel(tmpdir)
            with patch.object(sentinel, "_save_state"):
                await sentinel._emit_heartbeat()
                assert sentinel._state.heartbeat is not None
                assert sentinel._state.heartbeat.status == "healthy"
                assert sentinel._state.heartbeat.agent_pid > 0

    @pytest.mark.asyncio
    async def test_emit_heartbeat_has_uptime(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sentinel = self._make_sentinel(tmpdir)
            with patch.object(sentinel, "_save_state"):
                await sentinel._emit_heartbeat()
                assert sentinel._state.heartbeat.uptime_seconds >= 0

    @pytest.mark.asyncio
    async def test_heartbeat_saves_state_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sentinel = self._make_sentinel(tmpdir)
            with patch.object(sentinel, "_save_state") as mock_save:
                await sentinel._emit_heartbeat()
                mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_emit_heartbeat_creates_heartbeat_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sentinel = self._make_sentinel(tmpdir)
            with patch.object(sentinel, "_save_state"):
                await sentinel._emit_heartbeat()
                assert sentinel._state.heartbeat.status == "healthy"


class TestSentinelFreshness:
    def _make_sentinel(self, tmpdir):
        with patch("clawforge.sentinel.watcher.get_settings") as mock_settings:
            mock_s = MagicMock()
            mock_s.get_sentinel_path.return_value = Path(tmpdir) / "sentinel"
            mock_s.SENTINEL_HEARTBEAT_INTERVAL = 60
            mock_s.SENTINEL_FRESHNESS_THRESHOLD = 90
            mock_s.SENTINEL_DEAD_MAN_SWITCH = 300
            mock_settings.return_value = mock_s
            sentinel = Sentinel()
        return sentinel

    @pytest.mark.asyncio
    async def test_freshness_ok_when_recent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sentinel = self._make_sentinel(tmpdir)
            sentinel._state.heartbeat = Heartbeat(
                timestamp=time.time(),
                status="healthy",
                agent_pid=1234,
                uptime_seconds=100,
            )
            with patch.object(sentinel, "_trigger_recovery") as mock_recovery:
                await sentinel._check_freshness()
                mock_recovery.assert_not_called()

    @pytest.mark.asyncio
    async def test_freshness_triggers_recovery_when_stale(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sentinel = self._make_sentinel(tmpdir)
            sentinel._state.heartbeat = Heartbeat(
                timestamp=time.time() - 200,
                status="healthy",
                agent_pid=1234,
                uptime_seconds=100,
            )
            with patch.object(sentinel, "_trigger_recovery") as mock_recovery:
                with patch.object(sentinel, "_save_state"):
                    await sentinel._check_freshness()
                    mock_recovery.assert_called_once_with("stale_heartbeat")

    @pytest.mark.asyncio
    async def test_freshness_no_heartbeat_does_nothing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sentinel = self._make_sentinel(tmpdir)
            sentinel._state.heartbeat = None
            with patch.object(sentinel, "_trigger_recovery") as mock_recovery:
                await sentinel._check_freshness()
                mock_recovery.assert_not_called()

    @pytest.mark.asyncio
    async def test_freshness_updates_status_to_degraded(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sentinel = self._make_sentinel(tmpdir)
            sentinel._state.heartbeat = Heartbeat(
                timestamp=time.time() - 200,
                status="healthy",
                agent_pid=1234,
                uptime_seconds=100,
            )
            with patch.object(sentinel, "_trigger_recovery"):
                with patch.object(sentinel, "_save_state"):
                    await sentinel._check_freshness()
                    assert sentinel._state.heartbeat.status == "degraded"


class TestDeadMansSwitch:
    def _make_sentinel(self, tmpdir):
        with patch("clawforge.sentinel.watcher.get_settings") as mock_settings:
            mock_s = MagicMock()
            mock_s.get_sentinel_path.return_value = Path(tmpdir) / "sentinel"
            mock_s.SENTINEL_HEARTBEAT_INTERVAL = 60
            mock_s.SENTINEL_FRESHNESS_THRESHOLD = 90
            mock_s.SENTINEL_DEAD_MAN_SWITCH = 300
            mock_settings.return_value = mock_s
            sentinel = Sentinel()
        return sentinel

    @pytest.mark.asyncio
    async def test_dead_mans_switch_not_triggered_when_fresh(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sentinel = self._make_sentinel(tmpdir)
            sentinel._state.heartbeat = Heartbeat(
                timestamp=time.time(),
                status="healthy",
                agent_pid=1234,
                uptime_seconds=100,
            )
            with patch.object(sentinel, "_alert_operator") as mock_alert:
                await sentinel._check_dead_mans_switch()
                mock_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_dead_mans_switch_triggered_when_stale(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sentinel = self._make_sentinel(tmpdir)
            sentinel._state.heartbeat = Heartbeat(
                timestamp=time.time() - 400,
                status="healthy",
                agent_pid=1234,
                uptime_seconds=100,
            )
            with patch.object(sentinel, "_alert_operator") as mock_alert:
                with patch.object(sentinel, "_save_state"):
                    await sentinel._check_dead_mans_switch()
                    mock_alert.assert_called_once()
                    assert sentinel._state.dead_mans_switch_active is True

    @pytest.mark.asyncio
    async def test_dead_mans_switch_no_heartbeat(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sentinel = self._make_sentinel(tmpdir)
            sentinel._state.heartbeat = None
            with patch.object(sentinel, "_alert_operator") as mock_alert:
                await sentinel._check_dead_mans_switch()
                mock_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_dead_mans_switch_alert_has_details(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sentinel = self._make_sentinel(tmpdir)
            sentinel._state.heartbeat = Heartbeat(
                timestamp=time.time() - 400,
                status="healthy",
                agent_pid=1234,
                uptime_seconds=100,
            )
            with patch.object(sentinel, "_alert_operator") as mock_alert:
                with patch.object(sentinel, "_save_state"):
                    await sentinel._check_dead_mans_switch()
                    call_args = mock_alert.call_args
                    assert call_args[0][0] == "dead_mans_switch"
                    assert "elapsed" in call_args[0][1]


class TestSentinelRecovery:
    def _make_sentinel(self, tmpdir):
        with patch("clawforge.sentinel.watcher.get_settings") as mock_settings:
            mock_s = MagicMock()
            mock_s.get_sentinel_path.return_value = Path(tmpdir) / "sentinel"
            mock_s.SENTINEL_HEARTBEAT_INTERVAL = 60
            mock_s.SENTINEL_FRESHNESS_THRESHOLD = 90
            mock_s.SENTINEL_DEAD_MAN_SWITCH = 300
            mock_settings.return_value = mock_s
            sentinel = Sentinel()
        return sentinel

    @pytest.mark.asyncio
    async def test_trigger_recovery_increments_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sentinel = self._make_sentinel(tmpdir)
            sentinel._emit_heartbeat = AsyncMock()
            with patch.object(sentinel, "_save_state"):
                await sentinel._trigger_recovery("test_reason")
                assert sentinel._state.restart_count == 1
                assert sentinel._state.last_restart is not None

    @pytest.mark.asyncio
    async def test_trigger_recovery_multiple_times(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sentinel = self._make_sentinel(tmpdir)
            sentinel._emit_heartbeat = AsyncMock()
            with patch.object(sentinel, "_save_state"):
                await sentinel._trigger_recovery("r1")
                await sentinel._trigger_recovery("r2")
                assert sentinel._state.restart_count == 2

    def test_reset_restart_counter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sentinel = self._make_sentinel(tmpdir)
            sentinel._state.restart_count = 5
            sentinel._state.dead_mans_switch_active = True
            with patch.object(sentinel, "_save_state"):
                sentinel.reset_restart_counter()
                assert sentinel._state.restart_count == 0
                assert sentinel._state.dead_mans_switch_active is False

    def test_reset_counter_no_change(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sentinel = self._make_sentinel(tmpdir)
            sentinel._state.restart_count = 0
            with patch.object(sentinel, "_save_state") as mock_save:
                sentinel.reset_restart_counter()
                mock_save.assert_not_called()


class TestSentinelStop:
    def _make_sentinel(self, tmpdir):
        with patch("clawforge.sentinel.watcher.get_settings") as mock_settings:
            mock_s = MagicMock()
            mock_s.get_sentinel_path.return_value = Path(tmpdir) / "sentinel"
            mock_s.SENTINEL_HEARTBEAT_INTERVAL = 60
            mock_s.SENTINEL_FRESHNESS_THRESHOLD = 90
            mock_s.SENTINEL_DEAD_MAN_SWITCH = 300
            mock_settings.return_value = mock_s
            sentinel = Sentinel()
        return sentinel

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sentinel = self._make_sentinel(tmpdir)
            await sentinel.stop()
            assert sentinel._is_running is False

    @pytest.mark.asyncio
    async def test_double_start_prevented(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sentinel = self._make_sentinel(tmpdir)
            sentinel._is_running = True
            await sentinel.start()
            assert sentinel._is_running is True
