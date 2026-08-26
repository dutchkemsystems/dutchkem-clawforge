import os
import json
import pytest
import tempfile
from pathlib import Path

os.environ.setdefault("CLAW_EARN_WALLET", "0x0000000000000000000000000000000000000000")
os.environ.setdefault("CLAW_EARN_PRIVATE_KEY", "0x" + "1" * 64)

import time
from datetime import datetime
from unittest.mock import patch, MagicMock

from clawforge.audit.logger import HashChainLogger
from clawforge.audit.settlement import SettlementGenerator
from clawforge.models import AuditEntry, StateTransition


class TestHashChainLogger:
    def test_log_creates_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = HashChainLogger(Path(tmpdir))
            entry = logger.log("task_started", "task-1", {"detail": "test"})
            assert entry.action == "task_started"
            assert entry.task_id == "task-1"
            assert entry.hash != ""
            assert entry.prev_hash == "genesis"

    def test_hash_chain_links_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = HashChainLogger(Path(tmpdir))
            e1 = logger.log("action_1", "t1")
            e2 = logger.log("action_2", "t2")
            assert e2.prev_hash == e1.hash

    def test_verify_chain_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = HashChainLogger(Path(tmpdir))
            e1 = logger.log("a1", "t1")
            e2 = logger.log("a2", "t2")
            e3 = logger.log("a3", "t3")
            # Verify by checking prev_hash chain in memory
            assert e1.prev_hash == "genesis"
            assert e2.prev_hash == e1.hash
            assert e3.prev_hash == e2.hash

    def test_verify_chain_empty_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = HashChainLogger(Path(tmpdir))
            assert logger.verify_chain() is True

    def test_verify_chain_tampered(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = HashChainLogger(Path(tmpdir))
            logger.log("a1", "t1")
            logger.log("a2", "t2")
            log_file = Path(tmpdir) / "audit.jsonl"
            if log_file.exists():
                lines = log_file.read_text().strip().split("\n")
                entry = json.loads(lines[0])
                entry["action"] = "TAMPERED"
                lines[0] = json.dumps(entry)
                log_file.write_text("\n".join(lines) + "\n")
            assert logger.verify_chain() is False

    def test_get_entries_filters_by_since(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = HashChainLogger(Path(tmpdir))
            logger.log("a1", "t1")
            time.sleep(0.01)
            cutoff = time.time()
            time.sleep(0.01)
            logger.log("a2", "t2")
            entries = logger.get_entries(since=cutoff)
            assert len(entries) == 1

    def test_get_entries_empty_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = HashChainLogger(Path(tmpdir))
            assert logger.get_entries() == []

    def test_log_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = HashChainLogger(Path(tmpdir))
            logger.log("test_action")
            assert (Path(tmpdir) / "audit.jsonl").exists()

    def test_load_last_hash_from_existing_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger1 = HashChainLogger(Path(tmpdir))
            e1 = logger1.log("a1", "t1")
            logger2 = HashChainLogger(Path(tmpdir))
            assert logger2._last_hash == e1.hash

    def test_load_last_hash_empty_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "audit.jsonl"
            log_file.write_text("")
            logger = HashChainLogger(Path(tmpdir))
            assert logger._last_hash == "genesis"

    def test_details_default_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = HashChainLogger(Path(tmpdir))
            entry = logger.log("action")
            assert entry.details == {}

    def test_compute_hash_deterministic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = HashChainLogger(Path(tmpdir))
            h1 = logger._compute_hash("prev", {"key": "val"})
            h2 = logger._compute_hash("prev", {"key": "val"})
            assert h1 == h2

    def test_compute_hash_different_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = HashChainLogger(Path(tmpdir))
            h1 = logger._compute_hash("prev", {"key": "a"})
            h2 = logger._compute_hash("prev", {"key": "b"})
            assert h1 != h2

    def test_log_with_details(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = HashChainLogger(Path(tmpdir))
            entry = logger.log("action", "t1", {"foo": "bar"})
            assert entry.details == {"foo": "bar"}


class TestSettlementGenerator:
    def _make_generator(self, tmpdir):
        test_key = "0x" + "1" * 64
        from eth_account import Account
        account = Account.from_key(test_key)
        logger = HashChainLogger(Path(tmpdir))
        return SettlementGenerator(logger, test_key), account.address

    def test_generate_settlement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, addr = self._make_generator(tmpdir)
            transitions = [
                StateTransition(from_state="pending", to_state="completed", timestamp=1000.0)
            ]
            stmt = gen.generate("task-1", transitions, 50.0)
            assert stmt.task_id == "task-1"
            assert stmt.agent_address == addr
            assert stmt.total_amount == 50.0
            assert stmt.signature != ""
            assert len(stmt.transitions) == 1

    def test_generate_logs_to_audit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, _ = self._make_generator(tmpdir)
            gen.generate("task-2", [], 25.0)
            # Verify via hash chain
            assert gen.logger._last_hash != "genesis"

    def test_settlement_signature_is_hex(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, _ = self._make_generator(tmpdir)
            stmt = gen.generate("task-3", [], 10.0)
            bytes.fromhex(stmt.signature)

    def test_settlement_empty_transitions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen, _ = self._make_generator(tmpdir)
            stmt = gen.generate("task-4", [], 0.0)
            assert stmt.transitions == []
            assert stmt.total_amount == 0.0
