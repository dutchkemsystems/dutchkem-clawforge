"""Tests for on-chain settlement module."""
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from clawforge.settlement.onchain import (
    OnChainSettlement,
    SettlementQueue,
    OnChainSettler,
)


class TestOnChainSettlement:
    def test_create_settlement(self):
        s = OnChainSettlement(
            task_id="t1",
            from_address="0x" + "a" * 40,
            to_address="0x" + "b" * 40,
            amount_usdc=100.0,
        )
        assert s.task_id == "t1"
        assert s.status == "pending"
        assert s.amount_usdc == 100.0
        assert s.created_at > 0

    def test_settlement_model_dump(self):
        s = OnChainSettlement(
            task_id="t1",
            from_address="0x" + "a" * 40,
            to_address="0x" + "b" * 40,
            amount_usdc=50.0,
        )
        d = s.model_dump()
        assert d["task_id"] == "t1"
        assert d["amount_usdc"] == 50.0


class TestSettlementQueue:
    def test_enqueue_and_get_pending(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue = SettlementQueue(Path(tmpdir))
            s = OnChainSettlement(
                task_id="t1",
                from_address="0x" + "a" * 40,
                to_address="0x" + "b" * 40,
                amount_usdc=100.0,
            )
            queue.enqueue(s)
            pending = queue.get_pending()
            assert len(pending) == 1
            assert pending[0].task_id == "t1"

    def test_empty_queue(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue = SettlementQueue(Path(tmpdir))
            assert queue.get_pending() == []

    def test_mark_completed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue = SettlementQueue(Path(tmpdir))
            s = OnChainSettlement(
                task_id="t1",
                from_address="0x" + "a" * 40,
                to_address="0x" + "b" * 40,
                amount_usdc=100.0,
            )
            queue.enqueue(s)
            result = queue.mark_completed("t1", "0xabc", 12345, 0.001)
            assert result is True
            pending = queue.get_pending()
            assert len(pending) == 0

    def test_mark_completed_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue = SettlementQueue(Path(tmpdir))
            result = queue.mark_completed("nonexistent", "0xabc", 12345, 0.001)
            assert result is False

    def test_mark_failed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue = SettlementQueue(Path(tmpdir))
            s = OnChainSettlement(
                task_id="t1",
                from_address="0x" + "a" * 40,
                to_address="0x" + "b" * 40,
                amount_usdc=100.0,
            )
            queue.enqueue(s)
            result = queue.mark_failed("t1", "insufficient funds")
            assert result is True
            pending = queue.get_pending()
            assert len(pending) == 0

    def test_multiple_settlements(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue = SettlementQueue(Path(tmpdir))
            for i in range(3):
                s = OnChainSettlement(
                    task_id=f"t{i}",
                    from_address="0x" + "a" * 40,
                    to_address="0x" + "b" * 40,
                    amount_usdc=float(i * 10),
                )
                queue.enqueue(s)
            pending = queue.get_pending()
            assert len(pending) == 3
            queue.mark_completed("t1", "0xabc", 12345, 0.001)
            pending = queue.get_pending()
            assert len(pending) == 2

    def test_queue_persists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue = SettlementQueue(Path(tmpdir))
            s = OnChainSettlement(
                task_id="t1",
                from_address="0x" + "a" * 40,
                to_address="0x" + "b" * 40,
                amount_usdc=100.0,
            )
            queue.enqueue(s)
            # New queue instance reads same file
            queue2 = SettlementQueue(Path(tmpdir))
            pending = queue2.get_pending()
            assert len(pending) == 1


class TestOnChainSettler:
    def test_get_wallet_address(self):
        settler = OnChainSettler("0x" + "1" * 64)
        with patch("eth_account.Account.from_key") as mock_from_key:
            mock_account = MagicMock()
            mock_account.address = "0x" + "a" * 40
            mock_from_key.return_value = mock_account
            addr = settler.get_wallet_address()
            assert addr == "0x" + "a" * 40

    def test_create_settlement(self):
        settler = OnChainSettler("0x" + "1" * 64)
        with patch.object(settler, "get_wallet_address", return_value="0x" + "a" * 40):
            s = settler.create_settlement("t1", "0x" + "b" * 40, 100.0)
            assert s.task_id == "t1"
            assert s.amount_usdc == 100.0
            assert s.from_address == "0x" + "a" * 40
            assert s.to_address == "0x" + "b" * 40
            assert s.status == "pending"
