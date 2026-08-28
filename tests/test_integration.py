import asyncio
import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("CLAW_EARN_WALLET", "0x0000000000000000000000000000000000000000")
os.environ.setdefault("CLAW_EARN_PRIVATE_KEY", "0x" + "1" * 64)

from clawforge.audit.logger import HashChainLogger
from clawforge.audit.settlement import SettlementGenerator
from clawforge.economy.ledger import USDCLedger
from clawforge.economy.reputation import ReputationTracker
from clawforge.economy.staker import AutoStaker
from clawforge.execution.executor import WorkExecutor
from clawforge.execution.proof import ProofGenerator
from clawforge.models import Task
from clawforge.tasks.bidder import SmartBidder


def _make_task(task_id="task-1", value=50.0):
    return Task(
        id=task_id,
        title=f"Task {task_id}",
        description="Description",
        value_usdc=value,
        status="FUNDED",
        created_at=time.time(),
        required_skills=[],
        proof_type="sha256",
    )


def _mock_task(task_id="task-1", task_type="general", value=50.0):
    task = MagicMock(spec=Task)
    task.id = task_id
    task.title = f"Task {task_id}"
    task.value_usdc = value
    task.type = task_type
    return task


class TestFullTaskLifecycle:
    def test_complete_task_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_path = Path(tmpdir)

            ledger = USDCLedger(data_path / "economy")
            staker = AutoStaker(ledger, stake_percentage=0.10)
            reputation_path = data_path / "reputation"
            reputation_path.mkdir(parents=True, exist_ok=True)
            reputation = ReputationTracker(reputation_path)
            audit_logger = HashChainLogger(data_path / "audit")

            task = _make_task("task-lifecycle-1", value=100.0)

            audit_logger.log("task_discovered", task.id, {"value": 100.0})

            bidder = SmartBidder(reputation)
            assert hasattr(bidder, "calculate_bid")

            stake = staker.stake_for_task(task.id, float(task.value_usdc))
            assert stake == 10.0
            audit_logger.log("stake_recorded", task.id, {"stake": stake})

            executor = WorkExecutor(timeout=10.0)
            mock_task = _mock_task()
            result = asyncio.run(executor.execute(mock_task))
            assert result.success is True
            audit_logger.log("task_completed", task.id, {"output": result.output})

            proof_key = "0x" + "1" * 64
            proof_gen = ProofGenerator(proof_key)
            proof = proof_gen.generate(task.id, result.output)
            assert proof.task_id == task.id
            audit_logger.log("proof_generated", task.id, {"hash": proof.output_hash})

            test_key = "0x" + "1" * 64
            settlement_gen = SettlementGenerator(audit_logger, test_key)
            from clawforge.models import StateTransition
            transitions = [
                StateTransition(from_state="in_progress", to_state="completed", timestamp=time.time())
            ]
            settlement = settlement_gen.generate(task.id, transitions, float(task.value_usdc))
            assert settlement.signature != ""

            earned = float(task.value_usdc)
            ledger.append(task.id, earned, "credit", "Task completed")
            reclaim = staker.reclaim_stake(task.id)
            assert reclaim == stake

            balance = ledger.get_balance()
            assert balance == 100.0

    def test_low_inventory_triggers_study_tasks(self):
        from clawforge.tasks.sourcer import SupplyDemandScanner

        with tempfile.TemporaryDirectory() as tmpdir:
            warm = MagicMock()
            warm.get_frequent_entries.return_value = [
                MagicMock(key="pattern-1"),
                MagicMock(key="pattern-2"),
            ]
            scanner = SupplyDemandScanner(warm, Path(tmpdir))
            assert scanner.should_generate_study_tasks(3) is True
            tasks = scanner.generate_study_tasks(count=2)
            assert len(tasks) == 2
            assert all(t["type"] == "study" for t in tasks)

    def test_audit_chain_integrity(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = HashChainLogger(Path(tmpdir))
            e1 = logger.log("a1", "t1")
            e2 = logger.log("a2", "t2")
            e3 = logger.log("a3", "t3")
            assert e1.prev_hash == "genesis"
            assert e2.prev_hash == e1.hash
            assert e3.prev_hash == e2.hash

    def test_ledger_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = USDCLedger(Path(tmpdir))
            ledger.append("t1", 100.0, "credit")
            ledger.append("t2", 50.0, "credit")
            ledger_file = Path(tmpdir) / "ledger.jsonl"
            lines = ledger_file.read_text().strip().split("\n")
            entry = json.loads(lines[0])
            entry["amount"] = 99999.0
            lines[0] = json.dumps(entry)
            ledger_file.write_text("\n".join(lines) + "\n")
            ledger2 = USDCLedger(Path(tmpdir))
            assert ledger2.verify_chain() is False


class TestReputationEconomyFlow:
    def test_reputation_tier_progression(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rep_path = Path(tmpdir) / "reputation"
            rep_path.mkdir(parents=True, exist_ok=True)
            tracker = ReputationTracker(rep_path)

            assert tracker.profile.tier == "bronze"
            assert tracker.get_stake_percentage() == 0.30

            for _ in range(12):
                tracker.record_rating(5.0)
            assert tracker.profile.tier == "diamond"
            assert tracker.get_stake_percentage() == 0.10

    def test_ledger_append_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = USDCLedger(Path(tmpdir))
            ledger.append("t1", 100.0, "credit")
            ledger.append("t2", -20.0, "debit")
            ledger.append("t3", 50.0, "credit")
            assert ledger.get_balance() == 130.0
            assert ledger.verify_chain()
            entries = ledger.get_entries()
            assert len(entries) == 3


class TestSecuritySigning:
    def test_sign_and_verify_roundtrip(self):
        test_key = "0x" + "1" * 64
        from eth_account import Account

        from clawforge.crypto.signer import Signer
        account = Account.from_key(test_key)
        signer = Signer(test_key, account.address)

        sig = signer.sign_message("test message")
        assert signer.verify_signature("test message", sig) is True

    def test_verify_wrong_message_fails(self):
        test_key = "0x" + "1" * 64
        from eth_account import Account

        from clawforge.crypto.signer import Signer
        account = Account.from_key(test_key)
        signer = Signer(test_key, account.address)

        sig = signer.sign_message("correct message")
        assert signer.verify_signature("wrong message", sig) is False

    def test_sign_bid_and_proof(self):
        test_key = "0x" + "1" * 64
        from eth_account import Account

        from clawforge.crypto.signer import Signer
        account = Account.from_key(test_key)
        signer = Signer(test_key, account.address)

        bid_sig = signer.sign_task_bid("task-1", "50.0")
        assert len(bid_sig) > 0

        proof_sig = signer.sign_proof("task-1", "abc123", "12345")
        assert len(proof_sig) > 0

        settle_sig = signer.sign_settlement("task-1", "100.0", "10.0")
        assert len(settle_sig) > 0

    def test_vault_encrypt_decrypt_roundtrip(self):
        from clawforge.crypto.vault import Vault
        vault_key = "ab" * 32
        vault = Vault(vault_key)
        encrypted = vault.encrypt("my secret key")
        decrypted = vault.decrypt(encrypted)
        assert decrypted == "my secret key"

    def test_vault_wrong_key_fails(self):
        from clawforge.crypto.vault import Vault, VaultError
        v1 = Vault("ab" * 32)
        v2 = Vault("cd" * 32)
        encrypted = v1.encrypt("secret")
        with pytest.raises(VaultError):
            v2.decrypt(encrypted)

    def test_vault_invalid_key_rejected(self):
        from clawforge.crypto.vault import Vault, VaultError
        with pytest.raises(VaultError):
            Vault("short_key")
