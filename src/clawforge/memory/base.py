"""Base memory tier with shared logic for all memory tiers."""

import json
import time
from abc import ABC
from typing import Any

import structlog

from clawforge.config import get_settings
from clawforge.models import MemoryEntry

logger = structlog.get_logger(__name__)


class BaseMemory(ABC):
    """Base class for all memory tiers with shared CRUD operations."""

    def __init__(self, tier: str) -> None:
        """Initialize base memory tier.

        Args:
            tier: The memory tier name (hot, warm, cold).
        """
        self._tier = tier
        self._settings = get_settings()
        self._memory_path = self._settings.get_memory_path() / tier
        self._memory_path.mkdir(parents=True, exist_ok=True)
        self._entries: dict[str, MemoryEntry] = {}
        self._load_entries()

    def _load_entries(self) -> None:
        """Load all memory entries from disk."""
        for file_path in self._memory_path.glob("*.json"):
            try:
                data = json.loads(file_path.read_text())
                entry = MemoryEntry(**data)
                self._entries[entry.id] = entry
            except Exception as e:
                logger.warning(f"Failed to load {self._tier.upper()} entry", file=file_path.name, error=str(e))

        logger.debug(f"{self._tier.upper()} memory loaded", entries=len(self._entries))

    def get(self, key: str) -> Any | None:
        """Get value by key."""
        for entry in self._entries.values():
            if entry.key == key:
                entry.last_accessed = time.time()
                entry.access_count += 1
                self._save_entry(entry)
                return entry.value
        return None

    def retrieve(self, key: str) -> Any | None:
        """Retrieve value by key (alias for get)."""
        return self.get(key)

    def store(self, key: str, value: Any, tags: list[str] | None = None, timestamp: float | None = None) -> str:
        """Store a value in memory."""
        # Check if key already exists
        for entry in self._entries.values():
            if entry.key == key:
                entry.value = value
                entry.last_accessed = timestamp if timestamp is not None else time.time()
                entry.access_count += 1
                if tags:
                    entry.tags = tags
                self._save_entry(entry)
                return entry.id

        # Create new entry
        now = timestamp if timestamp is not None else time.time()
        entry_id = f"{self._tier}_{key}_{now}"
        entry = MemoryEntry(
            id=entry_id,
            tier=self._tier,
            key=key,
            value=value,
            created_at=now,
            last_accessed=now,
            access_count=1,
            tags=tags or [],
        )

        self._entries[entry_id] = entry
        self._save_entry(entry)

        logger.debug(f"{self._tier.upper()} entry created", key=key, id=entry_id)
        return entry_id

    def put(self, key: str, value: Any, tags: list[str] | None = None) -> str:
        """Store a value in memory (alias for store)."""
        return self.store(key, value, tags)

    def delete(self, key: str) -> bool:
        """Delete an entry by key."""
        for entry_id, entry in list(self._entries.items()):
            if entry.key == key:
                del self._entries[entry_id]
                file_path = self._memory_path / f"{entry_id}.json"
                if file_path.exists():
                    file_path.unlink()
                logger.debug(f"{self._tier.upper()} entry deleted", key=key)
                return True
        return False

    def list_keys(self) -> list[str]:
        """List all keys in memory."""
        return [entry.key for entry in self._entries.values()]

    def get_frequent_entries(self, min_accesses: int = 5, within_seconds: float = 3600) -> list[MemoryEntry]:
        """Get entries accessed frequently within time window."""
        threshold = time.time() - within_seconds
        return [
            entry for entry in self._entries.values()
            if entry.access_count >= min_accesses and entry.created_at >= threshold
        ]

    def _save_entry(self, entry: MemoryEntry) -> None:
        """Save entry to disk with atomic write."""
        file_path = self._memory_path / f"{entry.id}.json"
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
                file_path = self._memory_path / f"{entry_id}.json"
                if file_path.exists():
                    file_path.unlink()
                pruned += 1

        if pruned > 0:
            logger.info(f"{self._tier.upper()} memory pruned", entries=pruned)

        return pruned

    @property
    def size(self) -> int:
        """Get number of entries in memory."""
        return len(self._entries)
