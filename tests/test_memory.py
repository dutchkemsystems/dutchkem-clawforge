"""Tests for memory tiers (HOT, WARM, COLD)."""

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

os.environ.setdefault("CLAW_EARN_WALLET", "0x0000000000000000000000000000000000000000")
os.environ.setdefault("CLAW_EARN_PRIVATE_KEY", "0x" + "1" * 64)

from clawforge.memory.hot import HotMemory
from clawforge.memory.warm import WarmMemory
from clawforge.memory.cold import ColdMemory
from clawforge.models import MemoryEntry


class TestHotMemory:
    def _make_hot(self, tmpdir):
        mock_settings = type("Settings", (), {"get_memory_path": lambda self: Path(tmpdir) / "memory"})()
        with patch("clawforge.memory.hot.get_settings", return_value=mock_settings):
            return HotMemory()

    def test_store_and_retrieve(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_hot(tmpdir)
            mem.put("key1", {"value": "test"})
            result = mem.get("key1")
            assert result is not None
            assert result["value"] == "test"

    def test_prune_removes_old(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_hot(tmpdir)
            mem.put("key1", {"value": "old"})
            mem.prune(max_age_days=0)
            assert mem.get("key1") is None

    def test_get_nonexistent_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_hot(tmpdir)
            assert mem.get("nonexistent") is None

    def test_overwrite_existing_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_hot(tmpdir)
            mem.put("k1", "v1")
            mem.put("k1", "v2")
            assert mem.get("k1") == "v2"

    def test_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_hot(tmpdir)
            mem.put("k1", "v1")
            assert mem.delete("k1") is True
            assert mem.get("k1") is None

    def test_delete_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_hot(tmpdir)
            assert mem.delete("missing") is False

    def test_list_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_hot(tmpdir)
            mem.put("a", 1)
            mem.put("b", 2)
            keys = mem.list_keys()
            assert "a" in keys
            assert "b" in keys

    def test_size(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_hot(tmpdir)
            assert mem.size == 0
            mem.put("a", 1)
            assert mem.size == 1

    def test_put_with_tags(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_hot(tmpdir)
            entry_id = mem.put("k1", "v1", tags=["important"])
            assert entry_id is not None

    def test_get_increments_access_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_hot(tmpdir)
            mem.put("k1", "v1")
            mem.get("k1")
            mem.get("k1")
            assert mem.get("k1") == "v1"

    def test_prune_no_entries_to_prune(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_hot(tmpdir)
            assert mem.prune(max_age_days=30) == 0


class TestWarmMemory:
    def _make_warm(self, tmpdir):
        mock_settings = type("Settings", (), {"get_memory_path": lambda self: Path(tmpdir) / "memory"})()
        with patch("clawforge.memory.warm.get_settings", return_value=mock_settings):
            return WarmMemory()

    def test_in_memory_operations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_warm(tmpdir)
            now = time.time()
            e1 = MemoryEntry(
                id="w1", tier="warm", key="k1", value="v1",
                created_at=now, last_accessed=now, access_count=1, tags=["pattern"],
            )
            e2 = MemoryEntry(
                id="w2", tier="warm", key="k2", value="v2",
                created_at=now, last_accessed=now, access_count=1, tags=["other"],
            )
            mem._entries = {"w1": e1, "w2": e2}
            assert mem._entries["w1"].value == "v1"
            assert mem._entries["w2"].value == "v2"

    def test_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_warm(tmpdir)
            now = time.time()
            e = MemoryEntry(
                id="w1", tier="warm", key="k1", value="v1",
                created_at=now, last_accessed=now, access_count=1, tags=[],
            )
            mem._entries = {"w1": e}
            with patch("pathlib.Path.unlink"):
                assert mem.delete("k1") is True
                assert mem.get("k1") is None

    def test_delete_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_warm(tmpdir)
            assert mem.delete("missing") is False

    def test_list_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_warm(tmpdir)
            now = time.time()
            for k in ["a", "b"]:
                entry = MemoryEntry(
                    id=f"warm_{k}_0", tier="warm", key=k, value=1,
                    created_at=now, last_accessed=now, access_count=1, tags=[],
                )
                mem._entries[entry.id] = entry
            assert sorted(mem.list_keys()) == ["a", "b"]

    def test_get_by_tags(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_warm(tmpdir)
            now = time.time()
            e1 = MemoryEntry(
                id="w1", tier="warm", key="k1", value="v1",
                created_at=now, last_accessed=now, access_count=1, tags=["pattern"],
            )
            e2 = MemoryEntry(
                id="w2", tier="warm", key="k2", value="v2",
                created_at=now, last_accessed=now, access_count=1, tags=["other"],
            )
            mem._entries = {"w1": e1, "w2": e2}
            result = mem.get_by_tags(["pattern"])
            assert len(result) == 1
            assert result[0].key == "k1"

    def test_get_frequent_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_warm(tmpdir)
            now = time.time()
            e = MemoryEntry(
                id="w1", tier="warm", key="k1", value="v1",
                created_at=now, last_accessed=now, access_count=5, tags=[],
            )
            mem._entries = {"w1": e}
            result = mem.get_frequent_entries(min_accesses=2, within_seconds=3600)
            assert len(result) >= 1

    def test_prune(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_warm(tmpdir)
            old = time.time() - (60 * 86400)  # 60 days ago
            e = MemoryEntry(
                id="w1", tier="warm", key="k1", value="v1",
                created_at=old, last_accessed=old, access_count=1, tags=[],
            )
            mem._entries = {"w1": e}
            pruned = mem.prune(max_age_days=30)
            assert pruned == 1

    def test_size(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_warm(tmpdir)
            now = time.time()
            e = MemoryEntry(
                id="w1", tier="warm", key="a", value=1,
                created_at=now, last_accessed=now, access_count=1, tags=[],
            )
            mem._entries = {"w1": e}
            assert mem.size == 1


class TestColdMemory:
    def _make_cold(self, tmpdir):
        mock_settings = type("Settings", (), {"get_memory_path": lambda self: Path(tmpdir) / "memory"})()
        with patch("clawforge.memory.cold.get_settings", return_value=mock_settings):
            return ColdMemory()

    def test_in_memory_operations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_cold(tmpdir)
            now = time.time()
            e = MemoryEntry(
                id="cold_wallet_0", tier="cold", key="wallet", value="0x123",
                created_at=now, last_accessed=now, access_count=1, tags=[],
            )
            mem._entries = {e.id: e}
            assert mem._entries["cold_wallet_0"].value == "0x123"

    def test_get_identity(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_cold(tmpdir)
            now = time.time()
            e = MemoryEntry(
                id="cold_agent_identity_0", tier="cold", key="agent_identity",
                value={"address": "0x123"}, created_at=now, last_accessed=now,
                access_count=1, tags=["identity"],
            )
            mem._entries = {e.id: e}
            identity = mem._entries["cold_agent_identity_0"].value
            assert identity["address"] == "0x123"

    def test_get_reputation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_cold(tmpdir)
            now = time.time()
            e = MemoryEntry(
                id="cold_agent_reputation_0", tier="cold", key="agent_reputation",
                value={"score": 5.0}, created_at=now, last_accessed=now,
                access_count=1, tags=["reputation"],
            )
            mem._entries = {e.id: e}
            rep = mem._entries["cold_agent_reputation_0"].value
            assert rep["score"] == 5.0

    def test_append_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_cold(tmpdir)
            mem.append_history("task_completed", {"task_id": "t1"})
            history_file = Path(tmpdir) / "memory" / "cold" / "history.jsonl"
            assert history_file.exists()

    def test_prune_preserves_identity(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_cold(tmpdir)
            now = time.time()
            old = now - (400 * 86400)  # 400 days ago
            identity = MemoryEntry(
                id="c1", tier="cold", key="agent_identity", value={"addr": "0x1"},
                created_at=now, last_accessed=now, access_count=1, tags=["identity"],
            )
            temp = MemoryEntry(
                id="c2", tier="cold", key="temp_key", value="temp_value",
                created_at=old, last_accessed=old, access_count=1, tags=[],
            )
            mem._entries = {"c1": identity, "c2": temp}
            pruned = mem.prune(max_age_days=30)
            assert pruned == 1
            assert "c1" in mem._entries

    def test_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_cold(tmpdir)
            now = time.time()
            e = MemoryEntry(
                id="c1", tier="cold", key="k1", value="v1",
                created_at=now, last_accessed=now, access_count=1, tags=[],
            )
            mem._entries = {"c1": e}
            with patch("pathlib.Path.unlink"):
                assert mem.delete("k1") is True
                assert "c1" not in mem._entries

    def test_list_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_cold(tmpdir)
            now = time.time()
            e = MemoryEntry(
                id="c1", tier="cold", key="a", value=1,
                created_at=now, last_accessed=now, access_count=1, tags=[],
            )
            mem._entries = {"c1": e}
            assert "a" in mem.list_keys()

    def test_size(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_cold(tmpdir)
            now = time.time()
            for k in ["a", "b"]:
                e = MemoryEntry(
                    id=f"c_{k}", tier="cold", key=k, value=1,
                    created_at=now, last_accessed=now, access_count=1, tags=[],
                )
                mem._entries[e.id] = e
            assert mem.size == 2

    def test_overwrite_existing_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_cold(tmpdir)
            now = time.time()
            e = MemoryEntry(
                id="c1", tier="cold", key="k1", value="old",
                created_at=now, last_accessed=now, access_count=1, tags=[],
            )
            mem._entries = {"c1": e}
            mem._entries["c1"].value = "new"
            assert mem._entries["c1"].value == "new"

    def test_delete_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_cold(tmpdir)
            assert mem.delete("missing") is False

    def test_no_identity_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_cold(tmpdir)
            assert mem.get_identity() is None

    def test_no_reputation_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mem = self._make_cold(tmpdir)
            assert mem.get_reputation() is None
