"""COLD Memory Tier - Core identity and operating principles."""

import json
import time
from pathlib import Path
from typing import Any, Optional

import structlog

from clawforge.config import get_settings
from clawforge.models import MemoryEntry

logger = structlog.get_logger(__name__)


class ColdMemory:
    """COLD memory tier for identity, reputation, and history."""

    def __init__(self) -> None:
        """Initialize COLD memory."""
        self._settings = get_settings()
        self._cold_path = self._settings.get_memory_path() / "cold"
        self._cold_path.mkdir(parents=True, exist_ok=True)
        self._entries: dict[str, MemoryEntry] = {}
        self._load_entries()

    def _load_entries(self) -> None:
        """Load all COLD memory entries from disk."""
        for file_path in self._cold_path.glob("*.json"):
            try:
                data = json.loads(file_path.read_text())
                entry = MemoryEntry(**data)
                self._entries[entry.id] = entry
            except Exception as e:
                logger.warning("Failed to load COLD entry", file=file_path.name, error=str(e))

        logger.debug("COLD memory loaded", entries=len(self._entries))

    def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        for entry in self._entries.values():
            if entry.key == key:
                entry.last_accessed = time.time()
                entry.access_count += 1
                self._save_entry(entry)
                return entry.value
        return None

    def put(self, key: str, value: Any, tags: Optional[list[str]] = None) -> str:
        """Store a value in COLD memory."""
        # Check if key already exists
        for entry in self._entries.values():
            if entry.key == key:
                entry.value = value
                entry.last_accessed = time.time()
                entry.access_count += 1
                if tags:
                    entry.tags = tags
                self._save_entry(entry)
                return entry.id

        # Create new entry
        now = time.time()
        entry_id = f"cold_{key}_{now}"
        entry = MemoryEntry(
            id=entry_id,
            tier="cold",
            key=key,
            value=value,
            created_at=now,
            last_accessed=now,
            access_count=1,
            tags=tags or [],
        )

        self._entries[entry_id] = entry
        self._save_entry(entry)

        logger.debug("COLD entry created", key=key, id=entry_id)
        return entry_id

    def delete(self, key: str) -> bool:
        """Delete an entry by key."""
        for entry_id, entry in list(self._entries.items()):
            if entry.key == key:
                del self._entries[entry_id]
                file_path = self._cold_path / f"{entry_id}.json"
                if file_path.exists():
                    file_path.unlink()
                logger.debug("COLD entry deleted", key=key)
                return True
        return False

    def list_keys(self) -> list[str]:
        """List all keys in COLD memory."""
        return [entry.key for entry in self._entries.values()]

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
        history_file = self._cold_path / "history.jsonl"

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

    def _save_entry(self, entry: MemoryEntry) -> None:
        """Save entry to disk with atomic write."""
        file_path = self._cold_path / f"{entry.id}.json"
        temp_path = file_path.with_suffix(".tmp")

        data = entry.model_dump(mode="json")
        temp_path.write_text(json.dumps(data, indent=2))
        temp_path.replace(file_path)

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
                file_path = self._cold_path / f"{entry_id}.json"
                if file_path.exists():
                    file_path.unlink()
                pruned += 1

        if pruned > 0:
            logger.info("COLD memory pruned", entries=pruned)

        return pruned

    @property
    def size(self) -> int:
        """Get number of entries in COLD memory."""
        return len(self._entries)
