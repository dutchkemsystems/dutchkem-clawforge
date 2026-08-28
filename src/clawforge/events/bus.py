"""WebSocket event system for real-time task updates."""

import time
from typing import Any

from fastapi import WebSocket
from pydantic import BaseModel, Field


class Event(BaseModel):
    """Real-time event payload."""

    type: str
    task_id: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class EventBus:
    """In-memory event bus for broadcasting to WebSocket clients."""

    def __init__(self):
        self._subscribers: dict[str, list[WebSocket]] = {}
        self._global_subscribers: list[WebSocket] = []
        self._event_history: list[Event] = []
        self._max_history = 100

    async def connect(self, websocket: WebSocket, topic: str = "all") -> None:
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        if topic == "all":
            self._global_subscribers.append(websocket)
        else:
            if topic not in self._subscribers:
                self._subscribers[topic] = []
            self._subscribers[topic].append(websocket)

    def disconnect(self, websocket: WebSocket, topic: str = "all") -> None:
        """Remove a WebSocket connection."""
        if topic == "all":
            if websocket in self._global_subscribers:
                self._global_subscribers.remove(websocket)
        else:
            if topic in self._subscribers:
                if websocket in self._subscribers[topic]:
                    self._subscribers[topic].remove(websocket)

    async def publish(self, event: Event, topic: str = "all") -> None:
        """Publish an event to subscribers."""
        self._append_event(event)

        message = event.model_dump_json()
        dead: list[WebSocket] = []

        # Broadcast to global subscribers
        for ws in self._global_subscribers:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._global_subscribers.remove(ws)

        # Broadcast to topic subscribers
        if topic != "all" and topic in self._subscribers:
            dead = []
            for ws in self._subscribers[topic]:
                try:
                    await ws.send_text(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._subscribers[topic].remove(ws)

    def get_recent_events(self, limit: int = 50) -> list[Event]:
        """Get recent event history."""
        return self._event_history[-limit:]

    def _append_event(self, event: Event) -> None:
        """Append event with history trimming."""
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

    @property
    def subscriber_count(self) -> int:
        return len(self._global_subscribers) + sum(
            len(subs) for subs in self._subscribers.values()
        )


event_bus = EventBus()
