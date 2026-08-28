"""COLD Memory Tier - Core identity and operating principles."""

import json
import time
from pathlib import Path
from typing import Optional

import structlog

from .base import BaseMemory
from clawforge.models import MemoryEntry

logger = structlog.get_logger(__name__)


class ColdMemory(BaseMemory):
    """COLD memory tier for identity, reputation, and history."""

    def __init__(self) -> None:
        """Initialize COLD memory."""
        super().__init__("cold")

    def get_identity(self) -> Optional[dict]:
        """Get agent identity."""
        return self.get("agent_identity")

    def save_identity(self, identity: dict) -> str:
        """Save agent identity."""
        return self.put("agent_identity", identity, tags=["identity"])

    def get_reputation(self) -> Optional[dict]:
        """Get reputation data."""
        return self.get("agent_reputation")

    def save_reputation(self, reputation: dict) -> str:
        """Save reputation data."""
        return self.put("agent_reputation", reputation, tags=["reputation"])

    def append_history(self, action: str, details: dict) -> None:
        """Append to action history."""
        history_file = self._memory_path / "history.jsonl"

        entry = {
            "timestamp": time.time(),
            "action": action,
            "details": details,
        }

        existing = ""
        if history_file.exists():
            existing = history_file.read_text()

        temp = history_file.with_suffix(".tmp")
        temp.write_text(existing + json.dumps(entry) + "\n")
        temp.replace(history_file)

        logger.debug("History appended", action=action)

    def prune(self, max_age_days: int = 365) -> int:
        """Prune entries older than max_age_days."""
        threshold = time.time() - (max_age_days * 86400)
        pruned = 0

        for entry_id, entry in list(self._entries.items()):
            # Don't prune identity or reputation
            if entry.key in ["agent_identity", "agent_reputation"]:
                continue

            if entry.created_at < threshold:
                del self._entries[entry_id]
                file_path = self._memory_path / f"{entry_id}.json"
                if file_path.exists():
                    file_path.unlink()
                pruned += 1

        if pruned > 0:
            logger.info("COLD memory pruned", entries=pruned)

        return pruned
