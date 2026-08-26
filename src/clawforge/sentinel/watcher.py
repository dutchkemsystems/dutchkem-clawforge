"""Module 2: Self-healing sentinel watchdog."""

import json
import os
import time
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import structlog

from clawforge.config import get_settings
from clawforge.models import Heartbeat, SentinelState

logger = structlog.get_logger(__name__)


class Sentinel:
    """Self-healing sentinel watchdog with heartbeat and dead man's switch."""

    def __init__(self) -> None:
        """Initialize sentinel."""
        self._settings = get_settings()
        self._sentinel_path = self._settings.get_sentinel_path()
        self._sentinel_path.mkdir(parents=True, exist_ok=True)

        self._scheduler = AsyncIOScheduler()
        self._state = self._load_state()
        self._start_time = time.time()
        self._is_running = False

        logger.info("Sentinel initialized")

    def _load_state(self) -> SentinelState:
        """Load sentinel state from file."""
        state_file = self._sentinel_path / "state.json"

        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                return SentinelState(**data)
            except Exception as e:
                logger.warning("Failed to load sentinel state", error=str(e))

        return SentinelState()

    def _save_state(self) -> None:
        """Save sentinel state to file."""
        state_file = self._sentinel_path / "state.json"
        temp_path = state_file.with_suffix(".tmp")

        data = self._state.model_dump(mode="json")
        temp_path.write_text(json.dumps(data, indent=2))
        temp_path.replace(state_file)

    async def start(self) -> None:
        """Start the sentinel watchdog."""
        if self._is_running:
            logger.warning("Sentinel already running")
            return

        self._is_running = True

        # Schedule heartbeat job
        self._scheduler.add_job(
            self._emit_heartbeat,
            IntervalTrigger(seconds=self._settings.SENTINEL_HEARTBEAT_INTERVAL),
            id="heartbeat",
            replace_existing=True,
        )

        # Schedule freshness check
        self._scheduler.add_job(
            self._check_freshness,
            IntervalTrigger(seconds=30),
            id="freshness_check",
            replace_existing=True,
        )

        # Schedule dead man's switch check
        self._scheduler.add_job(
            self._check_dead_mans_switch,
            IntervalTrigger(seconds=60),
            id="dead_mans_switch",
            replace_existing=True,
        )

        self._scheduler.start()

        # Emit initial heartbeat
        await self._emit_heartbeat()

        logger.info(
            "Sentinel started",
            heartbeat_interval=self._settings.SENTINEL_HEARTBEAT_INTERVAL,
            freshness_threshold=self._settings.SENTINEL_FRESHNESS_THRESHOLD,
            dead_mans_switch=self._settings.SENTINEL_DEAD_MAN_SWITCH,
        )

    async def stop(self) -> None:
        """Stop the sentinel watchdog."""
        if not self._is_running:
            return

        self._scheduler.shutdown()
        self._is_running = False

        logger.info("Sentinel stopped")

    async def _emit_heartbeat(self) -> None:
        """Emit a heartbeat signal."""
        now = time.time()

        heartbeat = Heartbeat(
            timestamp=now,
            status="healthy",
            agent_pid=os.getpid(),
            uptime_seconds=int(now - self._start_time),
        )

        self._state.heartbeat = heartbeat
        self._save_state()

        # Save heartbeat to separate file for external monitoring
        heartbeat_file = self._sentinel_path / "heartbeat.json"
        temp_path = heartbeat_file.with_suffix(".tmp")
        temp_path.write_text(json.dumps(heartbeat.model_dump(mode="json"), indent=2))
        temp_path.replace(heartbeat_file)

        logger.debug(
            "Heartbeat emitted",
            status=heartbeat.status,
            uptime=heartbeat.uptime_seconds,
        )

    async def _check_freshness(self) -> None:
        """Check if heartbeat is fresh."""
        if not self._state.heartbeat:
            return

        now = time.time()
        last_heartbeat = self._state.heartbeat.timestamp
        elapsed = now - last_heartbeat

        if elapsed > self._settings.SENTINEL_FRESHNESS_THRESHOLD:
            logger.warning(
                "Heartbeat stale",
                elapsed=elapsed,
                threshold=self._settings.SENTINEL_FRESHNESS_THRESHOLD,
            )

            # Update status
            self._state.heartbeat.status = "degraded"
            self._save_state()

            # Trigger recovery
            await self._trigger_recovery("stale_heartbeat")

    async def _check_dead_mans_switch(self) -> None:
        """Check dead man's switch."""
        if not self._state.heartbeat:
            return

        now = time.time()
        last_heartbeat = self._state.heartbeat.timestamp
        elapsed = now - last_heartbeat

        if elapsed > self._settings.SENTINEL_DEAD_MAN_SWITCH:
            logger.critical(
                "DEAD MAN'S SWITCH TRIGGERED",
                elapsed=elapsed,
                threshold=self._settings.SENTINEL_DEAD_MAN_SWITCH,
            )

            self._state.dead_mans_switch_active = True
            self._save_state()

            # Alert operator
            await self._alert_operator("dead_mans_switch", {
                "elapsed": elapsed,
                "threshold": self._settings.SENTINEL_DEAD_MAN_SWITCH,
            })

    async def _trigger_recovery(self, reason: str) -> None:
        """Trigger process recovery."""
        self._state.restart_count += 1
        self._state.last_restart = time.time()
        self._save_state()

        logger.critical(
            "Triggering recovery",
            reason=reason,
            restart_count=self._state.restart_count,
        )

        # In production, this would restart the process
        # For now, we just log and reset heartbeat
        await self._emit_heartbeat()

    async def _alert_operator(self, alert_type: str, details: dict) -> None:
        """Alert operator of critical issue."""
        logger.critical(
            "OPERATOR ALERT",
            alert_type=alert_type,
            details=details,
        )

    def get_status(self) -> dict:
        """Get sentinel status."""
        return {
            "is_running": self._is_running,
            "restart_count": self._state.restart_count,
            "last_restart": self._state.last_restart,
            "dead_mans_switch_active": self._state.dead_mans_switch_active,
            "heartbeat": (
                self._state.heartbeat.model_dump(mode="json") if self._state.heartbeat else None
            ),
            "uptime_seconds": int(time.time() - self._start_time),
        }

    def reset_restart_counter(self) -> None:
        """Reset restart counter after stable operation."""
        if self._state.restart_count > 0:
            logger.info("Resetting restart counter")
            self._state.restart_count = 0
            self._state.dead_mans_switch_active = False
            self._save_state()


# Global sentinel instance
sentinel = Sentinel()
