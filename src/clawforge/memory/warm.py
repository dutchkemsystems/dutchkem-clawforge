"""WARM Memory Tier - Extracted lessons from completed tasks."""

from typing import Optional

import structlog

from .base import BaseMemory
from clawforge.models import MemoryEntry

logger = structlog.get_logger(__name__)


class WarmMemory(BaseMemory):
    """WARM memory tier for lessons learned and patterns."""

    def __init__(self) -> None:
        """Initialize WARM memory."""
        super().__init__("warm")

    def get_by_tags(self, tags: list[str]) -> list[MemoryEntry]:
        """Get entries matching any of the specified tags."""
        return [
            entry for entry in self._entries.values()
            if any(tag in entry.tags for tag in tags)
        ]

    def get_frequent_patterns(self, limit: int = 5) -> list[dict]:
        """Get most frequent access patterns for study task generation."""
        entries = sorted(self._entries.values(), key=lambda e: e.access_count, reverse=True)
        return [{"pattern": e.key, "count": e.access_count, "tags": e.tags} for e in entries[:limit]]
