"""WARM Memory Tier - Extracted lessons from completed tasks."""

import json
import time
from pathlib import Path
from typing import Any, Optional

import structlog

from clawforge.config import get_settings
from clawforge.models import MemoryEntry

logger = structlog.get_logger(__name__)


class WarmMemory:
    """WARM memory tier for lessons learned and patterns."""

    def __init__(self) -> None:
        """Initialize WARM memory."""
        self._settings = get_settings()
        self._warm_path = self._settings.get_memory_path() / "warm"
        self._warm_path.mkdir(parents=True, exist_ok=True)
        self._entries: dict[str, MemoryEntry] = {}
        self._load_entries()

    def _load_entries(self) -> None:
        """Load all WARM memory entries from disk."""
        for file_path in self._warm_path.glob("*.json"):
            try:
                data = json.loads(file_path.read_text())
                entry = MemoryEntry(**data)
                self._entries[entry.id] = entry
            except Exception as e:
                logger.warning("Failed to load WARM entry", file=file_path.name, error=str(e))

        logger.debug("WARM memory loaded", entries=len(self._entries))

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
        """Store a value in WARM memory."""
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
        entry_id = f"warm_{key}_{now}"
        entry = MemoryEntry(
            id=entry_id,
            tier="warm",
            key=key,
            value=value,
            created_at=now,
            last_accessed=now,
            access_count=1,
            tags=tags or [],
        )

        self._entries[entry_id] = entry
        self._save_entry(entry)

        logger.debug("WARM entry created", key=key, id=entry_id)
        return entry_id

    def delete(self, key: str) -> bool:
        """Delete an entry by key."""
        for entry_id, entry in list(self._entries.items()):
            if entry.key == key:
                del self._entries[entry_id]
                file_path = self._warm_path / f"{entry_id}.json"
                if file_path.exists():
                    file_path.unlink()
                logger.debug("WARM entry deleted", key=key)
                return True
        return False

    def list_keys(self) -> list[str]:
        """List all keys in WARM memory."""
        return [entry.key for entry in self._entries.values()]

    def get_by_tags(self, tags: list[str]) -> list[MemoryEntry]:
        """Get entries matching any of the specified tags."""
        return [
            entry for entry in self._entries.values()
            if any(tag in entry.tags for tag in tags)
        ]

    def get_frequent_entries(self, min_accesses: int = 5, within_seconds: float = 3600) -> list[MemoryEntry]:
        """Get entries accessed frequently within time window."""
        threshold = time.time() - within_seconds
        return [
            entry for entry in self._entries.values()
            if entry.access_count >= min_accesses and entry.last_accessed >= threshold
        ]

    def get_frequent_patterns(self, limit: int = 5) -> list[dict]:
        """Get most frequent access patterns for study task generation."""
        entries = sorted(self._entries.values(), key=lambda e: e.access_count, reverse=True)
        return [{"pattern": e.key, "count": e.access_count, "tags": e.tags} for e in entries[:limit]]

    def _save_entry(self, entry: MemoryEntry) -> None:
        """Save entry to disk with atomic write."""
        file_path = self._warm_path / f"{entry.id}.json"
        temp_path = file_path.with_suffix(".tmp")

        data = entry.model_dump(mode="json")
        temp_path.write_text(json.dumps(data, indent=2))
        temp_path.replace(file_path)

    def prune(self, max_age_days: int = 30) -> int:
        """Prune entries older than max_age_days."""
        threshold = time.time() - (max_age_days * 86400)
        pruned = 0

        for entry_id, entry in list(self._entries.items()):
            if entry.created_at < threshold:
                del self._entries[entry_id]
                file_path = self._warm_path / f"{entry_id}.json"
                if file_path.exists():
                    file_path.unlink()
                pruned += 1

        if pruned > 0:
            logger.info("WARM memory pruned", entries=pruned)

        return pruned

    @property
    def size(self) -> int:
        """Get number of entries in WARM memory."""
        return len(self._entries)
