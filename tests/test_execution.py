import os
import asyncio
import time
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

os.environ.setdefault("CLAW_EARN_WALLET", "0x0000000000000000000000000000000000000000")
os.environ.setdefault("CLAW_EARN_PRIVATE_KEY", "0x" + "1" * 64)

from clawforge.execution.executor import WorkExecutor, AGENT_DISPATCH
from clawforge.execution.proof import ProofGenerator
from clawforge.execution.a2a import A2AQueue
from clawforge.models import Task, AgentType, Subtask


def _make_task(task_id="task-1", value=50.0):
    return Task(
        id=task_id,
        title=f"Test Task {task_id}",
        description="Test description",
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


class TestWorkExecutor:
    @pytest.mark.asyncio
    async def test_execute_success(self):
        executor = WorkExecutor(timeout=10.0)
        task = _mock_task()
        result = await executor.execute(task)
        assert result.success is True
        assert result.task_id == "task-1"
        assert result.execution_time > 0

    @pytest.mark.asyncio
    async def test_execute_timeout(self):
        executor = WorkExecutor(timeout=0.01)
        task = _mock_task()

        async def slow_work(agent_type, task):
            await asyncio.sleep(10)
            return "done"

        with patch.object(executor, "_dispatch_work", side_effect=slow_work):
            result = await executor.execute(task)
            assert result.success is False
            assert result.error == "Execution timeout"

    @pytest.mark.asyncio
    async def test_execute_dispatches_to_correct_agent_type(self):
        executor = WorkExecutor(timeout=10.0)
        task = _mock_task(task_type="sales")
        result = await executor.execute(task)
        assert result.agent_type == AgentType.SALES

    @pytest.mark.asyncio
    async def test_execute_unknown_type_defaults_to_general(self):
        executor = WorkExecutor(timeout=10.0)
        task = _mock_task(task_type="unknown_type")
        result = await executor.execute(task)
        assert result.agent_type == AgentType.GENERAL

    @pytest.mark.asyncio
    async def test_execute_kyc_type(self):
        executor = WorkExecutor(timeout=10.0)
        task = _mock_task(task_type="kyc")
        result = await executor.execute(task)
        assert result.agent_type == AgentType.KYC_AML

    @pytest.mark.asyncio
    async def test_execute_ecommerce_type(self):
        executor = WorkExecutor(timeout=10.0)
        task = _mock_task(task_type="ecommerce")
        result = await executor.execute(task)
        assert result.agent_type == AgentType.ECOMMERCE

    def test_agent_dispatch_mapping(self):
        assert AGENT_DISPATCH["sales"] == AgentType.SALES
        assert AGENT_DISPATCH["kyc"] == AgentType.KYC_AML
        assert AGENT_DISPATCH["ecommerce"] == AgentType.ECOMMERCE
        assert AGENT_DISPATCH["general"] == AgentType.GENERAL

    @pytest.mark.asyncio
    async def test_execute_returns_output(self):
        executor = WorkExecutor(timeout=10.0)
        task = _mock_task()
        result = await executor.execute(task)
        assert "task-1" in result.output

    @pytest.mark.asyncio
    async def test_execute_records_timing(self):
        executor = WorkExecutor(timeout=10.0)
        task = _mock_task()
        result = await executor.execute(task)
        assert result.execution_time >= 0


class TestProofGenerator:
    def _make_generator(self):
        test_key = "0x" + "1" * 64
        from eth_account import Account
        account = Account.from_key(test_key)
        return ProofGenerator(test_key), account.address

    def test_generate_sha256_proof(self):
        gen, addr = self._make_generator()
        proof = gen.generate("task-1", "output data", on_chain=False)
        assert proof.task_id == "task-1"
        assert len(proof.output_hash) == 64
        assert proof.agent_signature is not None
        assert len(proof.agent_signature) > 0
        assert proof.metadata["on_chain"] is False

    def test_generate_keccak256_proof(self):
        gen, addr = self._make_generator()
        proof = gen.generate("task-2", "output data", on_chain=True)
        assert proof.task_id == "task-2"
        assert proof.output_hash.startswith("0x")
        assert len(proof.output_hash) == 66
        assert proof.metadata["on_chain"] is True

    def test_proof_includes_agent_address(self):
        gen, addr = self._make_generator()
        proof = gen.generate("task-3", "data")
        assert proof.metadata["agent_address"] == addr

    def test_proof_deterministic_same_input(self):
        gen, _ = self._make_generator()
        p1 = gen.generate("task-x", "same output")
        p2 = gen.generate("task-x", "same output")
        assert p1.output_hash == p2.output_hash

    def test_proof_different_for_different_output(self):
        gen, _ = self._make_generator()
        p1 = gen.generate("task-1", "output A")
        p2 = gen.generate("task-1", "output B")
        assert p1.output_hash != p2.output_hash

    def test_proof_timestamp_is_reasonable(self):
        gen, _ = self._make_generator()
        before = time.time()
        proof = gen.generate("task-1", "data")
        after = time.time()
        assert before <= proof.timestamp <= after


class TestA2AQueue:
    @pytest.mark.asyncio
    async def test_post_bounty_creates_subtask(self):
        q = A2AQueue()
        subtask = await q.post_bounty("test desc", "sales", 10.0)
        assert subtask.description == "test desc"
        assert subtask.type == "sales"
        assert subtask.value_usdc == 10.0

    @pytest.mark.asyncio
    async def test_process_next_empty_queue(self):
        q = A2AQueue()
        result = await q.process_next()
        assert result is None

    @pytest.mark.asyncio
    async def test_process_next_with_handler(self):
        q = A2AQueue()

        async def handler(subtask):
            return "completed"

        q.register_handler("sales", handler)
        await q.post_bounty("test", "sales", 5.0)
        subtask, result = await q.process_next()
        assert subtask.type == "sales"
        assert result == "completed"

    @pytest.mark.asyncio
    async def test_process_next_no_handler(self):
        q = A2AQueue()
        await q.post_bounty("test", "unknown", 5.0)
        subtask, result = await q.process_next()
        assert result == "No handler registered"

    @pytest.mark.asyncio
    async def test_post_bounty_subtask_has_id(self):
        q = A2AQueue()
        subtask = await q.post_bounty("test", "a", 1.0)
        assert subtask.id.startswith("a2a-")

    @pytest.mark.asyncio
    async def test_handler_is_called(self):
        q = A2AQueue()
        call_tracker = []

        async def handler(st):
            call_tracker.append(st.description)
            return "ok"

        q.register_handler("x", handler)
        await q.post_bounty("first", "x", 1.0)
        result = await q.process_next()
        assert result is not None
        assert call_tracker == ["first"]

    @pytest.mark.asyncio
    async def test_subtask_created_at_timestamp(self):
        q = A2AQueue()
        before = time.time()
        subtask = await q.post_bounty("t", "a", 1.0)
        after = time.time()
        assert before <= subtask.created_at <= after
