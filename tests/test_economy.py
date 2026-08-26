import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from clawforge.economy.ledger import USDCLedger
from clawforge.economy.staker import AutoStaker
from clawforge.economy.reputation import ReputationTracker


class TestUSDCLedger:
    def test_append_and_balance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = USDCLedger(Path(tmpdir))
            ledger.append("task-1", 100.0, "credit", "Task completed")
            ledger.append("task-1", -10.0, "stake", "Auto-stake")
            assert ledger.get_balance() == 90.0

    def test_hash_chain_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = USDCLedger(Path(tmpdir))
            ledger.append("task-1", 100.0, "credit")
            ledger.append("task-2", 50.0, "credit")
            assert ledger.verify_chain() is True

    def test_empty_ledger_balance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = USDCLedger(Path(tmpdir))
            assert ledger.get_balance() == 0.0

    def test_empty_ledger_verify_chain(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = USDCLedger(Path(tmpdir))
            assert ledger.verify_chain() is True

    def test_get_entries_filters_by_task_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = USDCLedger(Path(tmpdir))
            ledger.append("t1", 10.0, "credit")
            ledger.append("t2", 20.0, "credit")
            ledger.append("t1", 5.0, "debit")
            entries = ledger.get_entries(task_id="t1")
            assert len(entries) == 2

    def test_get_entries_filters_by_since(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = USDCLedger(Path(tmpdir))
            ledger.append("t1", 10.0, "credit")
            import time
            time.sleep(0.01)
            cutoff = time.time()
            time.sleep(0.01)
            ledger.append("t2", 20.0, "credit")
            entries = ledger.get_entries(since=cutoff)
            assert len(entries) == 1

    def test_hash_chain_tamper_detection(self):
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

    def test_multiple_entries_balance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = USDCLedger(Path(tmpdir))
            for i in range(5):
                ledger.append(f"t{i}", 10.0, "credit")
            assert ledger.get_balance() == 50.0

    def test_ledger_persists_across_instances(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger1 = USDCLedger(Path(tmpdir))
            ledger1.append("t1", 100.0, "credit")
            ledger2 = USDCLedger(Path(tmpdir))
            assert ledger2.get_balance() == 100.0


class TestAutoStaker:
    def test_stake_for_task(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = USDCLedger(Path(tmpdir))
            staker = AutoStaker(ledger, stake_percentage=0.10)
            stake = staker.stake_for_task("task-1", 100.0)
            assert stake == 10.0

    def test_stake_deducted_from_balance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = USDCLedger(Path(tmpdir))
            ledger.append("t1", 100.0, "credit")
            staker = AutoStaker(ledger, stake_percentage=0.10)
            staker.stake_for_task("t1", 100.0)
            assert ledger.get_balance() == 90.0

    def test_reclaim_stake(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = USDCLedger(Path(tmpdir))
            staker = AutoStaker(ledger, stake_percentage=0.10)
            staker.stake_for_task("t1", 100.0)
            reclaimed = staker.reclaim_stake("t1")
            assert reclaimed == 10.0

    def test_reclaim_nonexistent_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = USDCLedger(Path(tmpdir))
            staker = AutoStaker(ledger, stake_percentage=0.10)
            assert staker.reclaim_stake("nonexistent") == 0.0

    def test_reclaim_already_reclaimed_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = USDCLedger(Path(tmpdir))
            staker = AutoStaker(ledger, stake_percentage=0.10)
            staker.stake_for_task("t1", 100.0)
            staker.reclaim_stake("t1")
            assert staker.reclaim_stake("t1") == 0.0

    def test_execute_rate_and_claim(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = USDCLedger(Path(tmpdir))
            staker = AutoStaker(ledger, stake_percentage=0.10)
            staker.stake_for_task("t1", 100.0)
            result = staker.execute_rate_and_claim("t1")
            assert result == 10.0

    def test_get_staked_amount(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = USDCLedger(Path(tmpdir))
            staker = AutoStaker(ledger, stake_percentage=0.10)
            staker.stake_for_task("t1", 100.0)
            staker.stake_for_task("t2", 200.0)
            assert staker.get_staked_amount() == 30.0

    def test_get_staked_amount_after_reclaim(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = USDCLedger(Path(tmpdir))
            staker = AutoStaker(ledger, stake_percentage=0.10)
            staker.stake_for_task("t1", 100.0)
            staker.reclaim_stake("t1")
            assert staker.get_staked_amount() == 0.0

    def test_stake_zero_value_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = USDCLedger(Path(tmpdir))
            staker = AutoStaker(ledger, stake_percentage=0.10)
            assert staker.stake_for_task("t1", 0.0) == 0.0

    def test_staker_persists_across_instances(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = USDCLedger(Path(tmpdir))
            staker1 = AutoStaker(ledger, stake_percentage=0.10)
            staker1.stake_for_task("t1", 100.0)
            staker2 = AutoStaker(ledger, stake_percentage=0.10)
            assert staker2.get_staked_amount() == 10.0


class TestReputationTracker:
    def test_default_bronze(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ReputationTracker(Path(tmpdir))
            assert tracker.profile.tier == "bronze"
            assert tracker.get_stake_percentage() == 0.30

    def test_record_rating_updates_profile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ReputationTracker(Path(tmpdir))
            tracker.record_rating(4.0)
            assert tracker.profile.total_ratings == 1
            assert tracker.profile.average_rating == 4.0

    def test_tier_upgrade_to_silver(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ReputationTracker(Path(tmpdir))
            for _ in range(6):
                tracker.record_rating(3.5)
            assert tracker.profile.tier == "silver"
            assert tracker.get_stake_percentage() == 0.25

    def test_tier_upgrade_to_gold(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ReputationTracker(Path(tmpdir))
            for _ in range(6):
                tracker.record_rating(4.5)
            assert tracker.profile.tier == "gold"
            assert tracker.get_stake_percentage() == 0.20

    def test_tier_upgrade_to_diamond(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ReputationTracker(Path(tmpdir))
            for _ in range(12):
                tracker.record_rating(5.0)
            assert tracker.profile.tier == "diamond"
            assert tracker.get_stake_percentage() == 0.10

    def test_persists_across_instances(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            t1 = ReputationTracker(Path(tmpdir))
            t1.record_rating(4.0)
            t2 = ReputationTracker(Path(tmpdir))
            assert t2.profile.total_ratings == 1
            assert t2.profile.average_rating == 4.0

    def test_low_ratings_stay_bronze(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ReputationTracker(Path(tmpdir))
            for _ in range(10):
                tracker.record_rating(1.0)
            assert tracker.profile.tier == "bronze"
