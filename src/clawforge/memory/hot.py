"""HOT Memory Tier - Real-time operational state."""

from typing import Any, Optional

import structlog

from .base import BaseMemory
from clawforge.models import MemoryEntry

logger = structlog.get_logger(__name__)


class HotMemory(BaseMemory):
    """HOT memory tier for real-time task state and conversation context."""

    def __init__(self) -> None:
        """Initialize HOT memory."""
        super().__init__("hot")

    def get_stale_entries(self, idle_seconds: float = 1800) -> list[MemoryEntry]:
        """Get entries that have been idle for specified seconds."""
        threshold = __import__('time').time() - idle_seconds
        return [
            entry for entry in self._entries.values()
            if entry.last_accessed < threshold
        ]
