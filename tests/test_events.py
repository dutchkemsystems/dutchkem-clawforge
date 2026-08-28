"""Tests for WebSocket event bus."""
from clawforge.events.bus import Event, EventBus


class TestEventBus:
    def test_create_event(self):
        e = Event(type="test", task_id="t1", data={"key": "value"})
        assert e.type == "test"
        assert e.task_id == "t1"
        assert e.timestamp > 0

    def test_event_history(self):
        bus = EventBus()
        for i in range(5):
            bus._event_history.append(Event(type=f"event_{i}"))
        recent = bus.get_recent_events(3)
        assert len(recent) == 3
        assert recent[0].type == "event_2"

    def test_event_history_empty(self):
        bus = EventBus()
        assert bus.get_recent_events() == []

    def test_subscriber_count_empty(self):
        bus = EventBus()
        assert bus.subscriber_count == 0

    def test_max_history(self):
        bus = EventBus()
        bus._max_history = 3
        for i in range(10):
            bus._append_event(Event(type=f"event_{i}"))
        assert len(bus._event_history) == 3

    def test_event_model_dump(self):
        e = Event(type="task_bid", task_id="t1", data={"amount": 50.0})
        d = e.model_dump()
        assert d["type"] == "task_bid"
        assert d["task_id"] == "t1"
        assert d["data"]["amount"] == 50.0
