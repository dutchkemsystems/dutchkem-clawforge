"""FastAPI routes for Clawforge API."""

import re
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..config import get_settings
from ..models import (
    AuditEntry,
    LedgerEntry,
    SettlementStatement,
    Task,
)
from ..economy.ledger import USDCLedger
from ..economy.staker import AutoStaker
from ..economy.reputation import ReputationTracker
from ..memory.hot import HotMemory
from ..sentinel.watcher import sentinel
from ..protocol.trust import trust_boundary
from ..events.bus import event_bus, Event
from ..execution.executor import WorkExecutor

router = APIRouter(prefix="/v1", tags=["clawforge"])

# Input validation patterns
_TASK_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")
_ADDRESS_PATTERN = re.compile(r"^0x[0-9a-fA-F]{40}$")

# Lazy-loaded singletons
_ledger: Optional[USDCLedger] = None
_staker: Optional[AutoStaker] = None
_reputation: Optional[ReputationTracker] = None
_hot: Optional[HotMemory] = None


def _get_ledger() -> USDCLedger:
    global _ledger
    if _ledger is None:
        settings = get_settings()
        _ledger = USDCLedger(settings.get_economy_path())
    return _ledger


def _get_staker() -> AutoStaker:
    global _staker
    if _staker is None:
        _staker = AutoStaker(_get_ledger())
    return _staker


def _get_reputation() -> ReputationTracker:
    global _reputation
    if _reputation is None:
        settings = get_settings()
        _reputation = ReputationTracker(settings.get_economy_path())
    return _reputation


def _get_hot() -> HotMemory:
    global _hot
    if _hot is None:
        _hot = HotMemory()
    return _hot


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "clawforge", "timestamp": time.time()}


@router.get("/tasks")
async def list_tasks(status: str = Query("FUNDED")):
    """List tasks from cache."""
    hot = _get_hot()
    cached_tasks = hot.get("cached_tasks")
    if cached_tasks:
        filtered = [t for t in cached_tasks if t.get("status") == status]
        return {"tasks": filtered, "count": len(filtered)}
    return {"tasks": [], "count": 0}


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get task details."""
    if not _TASK_ID_PATTERN.match(task_id):
        raise HTTPException(status_code=400, detail="Invalid task_id format")
    hot = _get_hot()
    cached_tasks = hot.get("cached_tasks") or []
    for task in cached_tasks:
        if task.get("id") == task_id:
            return task
    raise HTTPException(status_code=404, detail="Task not found")


@router.post("/tasks/{task_id}/bid")
async def bid_on_task(task_id: str, bid_amount: float):
    """Submit a bid on a task."""
    if not _TASK_ID_PATTERN.match(task_id):
        raise HTTPException(status_code=400, detail="Invalid task_id format")
    if bid_amount <= 0 or bid_amount > 10000:
        raise HTTPException(status_code=400, detail="Bid amount must be between 0 and 10000 USDC")
    rep = _get_reputation()

    staker = _get_staker()
    stake = staker.stake_for_task(task_id, bid_amount)

    return {
        "task_id": task_id,
        "bid_amount": bid_amount,
        "stake_amount": stake,
        "status": "submitted",
        "timestamp": time.time(),
    }


@router.post("/tasks/{task_id}/submit")
async def submit_proof(task_id: str):
    """Submit proof of work completion."""
    if not _TASK_ID_PATTERN.match(task_id):
        raise HTTPException(status_code=400, detail="Invalid task_id format")
    return {
        "task_id": task_id,
        "status": "proof_submitted",
        "timestamp": time.time(),
    }


@router.post("/tasks/{task_id}/stake-reclaim")
async def reclaim_stake(task_id: str):
    """Reclaim staked USDC after task completion."""
    if not _TASK_ID_PATTERN.match(task_id):
        raise HTTPException(status_code=400, detail="Invalid task_id format")
    staker = _get_staker()
    reclaimed = staker.execute_rate_and_claim(task_id)
    return {
        "task_id": task_id,
        "reclaimed_amount": reclaimed,
        "status": "reclaimed" if reclaimed > 0 else "no_stake_found",
        "timestamp": time.time(),
    }


@router.get("/ledger")
async def get_ledger(task_id: Optional[str] = None, since: Optional[float] = None):
    """Get ledger entries."""
    ledger = _get_ledger()
    entries = ledger.get_entries(task_id=task_id, since=since)
    return {"entries": [e.model_dump() for e in entries], "count": len(entries)}


@router.get("/ledger/balance")
async def get_balance():
    """Get current USDC balance."""
    ledger = _get_ledger()
    staker = _get_staker()
    return {
        "balance": ledger.get_balance(),
        "staked": staker.get_staked_amount(),
        "currency": "USDC",
    }


@router.get("/audit")
async def get_audit_log(task_id: str = "", since: float = 0):
    """Get audit log entries."""
    return {"entries": [], "count": 0, "message": "Audit logger available via HashChainLogger class"}


@router.get("/audit/verify")
async def verify_audit_chain():
    """Verify audit log hash chain integrity."""
    ledger = _get_ledger()
    valid = ledger.verify_chain()
    return {"valid": valid, "timestamp": time.time()}


@router.get("/settlement/{task_id}")
async def get_settlement(task_id: str):
    """Get settlement statement for a task."""
    if not _TASK_ID_PATTERN.match(task_id):
        raise HTTPException(status_code=400, detail="Invalid task_id format")
    ledger = _get_ledger()
    entries = ledger.get_entries(task_id=task_id)
    if not entries:
        raise HTTPException(status_code=404, detail="No entries found for task")
    return {
        "task_id": task_id,
        "entries": [e.model_dump() for e in entries],
        "total_amount": sum(e.amount for e in entries),
    }


@router.get("/sentinel/status")
async def sentinel_status():
    """Get sentinel watchdog status."""
    return sentinel.get_status()


@router.get("/reputation")
async def get_reputation():
    """Get agent reputation profile."""
    rep = _get_reputation()
    return rep.profile.model_dump()


@router.post("/reputation/rate")
async def rate_task(task_id: str, rating: float):
    """Rate a completed task."""
    if rating < 0 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 0 and 5")

    rep = _get_reputation()
    tier = rep.record_rating(rating)
    return {
        "task_id": task_id,
        "rating": rating,
        "new_tier": tier,
        "profile": rep.profile.model_dump(),
    }


@router.get("/trust/pending-approvals")
async def get_pending_approvals():
    """Get pending trust boundary approval requests."""
    return {"approvals": trust_boundary.get_pending_approvals()}


@router.post("/trust/approve/{index}")
async def approve_trust_request(index: int):
    """Approve a trust boundary violation request."""
    success = trust_boundary.approve_request(index)
    if not success:
        raise HTTPException(status_code=404, detail="Request not found or already processed")
    return {"index": index, "status": "approved"}


@router.post("/trust/reject/{index}")
async def reject_trust_request(index: int):
    """Reject a trust boundary violation request."""
    success = trust_boundary.reject_request(index)
    if not success:
        raise HTTPException(status_code=404, detail="Request not found or already processed")
    return {"index": index, "status": "rejected"}


# --- Task Execution ---


@router.post("/tasks/{task_id}/execute")
async def execute_task(task_id: str):
    """Execute a task using the AI agent executor.

    Dispatches to the appropriate agent type (sales, kyc, ecommerce, general)
    based on the task type. Requires OPENAI_API_KEY for real execution,
    falls back to stub output otherwise.
    """
    if not _TASK_ID_PATTERN.match(task_id):
        raise HTTPException(status_code=400, detail="Invalid task_id format")
    executor = WorkExecutor(timeout=300.0)
    task = Task(
        id=task_id,
        title=f"Task {task_id}",
        description="Execute task via API",
        value_usdc=0.0,
        type="general",
        created_at=time.time(),
    )
    result = await executor.execute(task)

    await event_bus.publish(Event(
        type="task_executed",
        task_id=task_id,
        data={
            "success": result.success,
            "execution_time": result.execution_time,
            "agent_type": result.agent_type.value,
        },
    ))

    return {
        "task_id": task_id,
        "success": result.success,
        "output": result.output,
        "execution_time": result.execution_time,
        "agent_type": result.agent_type.value,
        "error": result.error,
    }


# --- On-Chain Settlement ---


@router.post("/settlement/{task_id}/submit")
async def submit_settlement(task_id: str, to_address: str, amount_usdc: float):
    """Submit an on-chain USDC settlement for a task.

    Creates a settlement record and queues it for broadcast on Base chain.
    """
    if not _TASK_ID_PATTERN.match(task_id):
        raise HTTPException(status_code=400, detail="Invalid task_id format")
    if not _ADDRESS_PATTERN.match(to_address):
        raise HTTPException(status_code=400, detail="Invalid Ethereum address format")
    if amount_usdc <= 0 or amount_usdc > 100000:
        raise HTTPException(status_code=400, detail="Amount must be between 0 and 100000 USDC")
    from ..settlement.onchain import create_settler, SettlementQueue
    from pathlib import Path

    settler = create_settler()
    settlement = settler.create_settlement(task_id, to_address, amount_usdc)

    queue = SettlementQueue(Path("./data/settlement"))
    queue.enqueue(settlement)

    await event_bus.publish(Event(
        type="settlement_submitted",
        task_id=task_id,
        data={"to_address": to_address, "amount_usdc": amount_usdc},
    ))

    return {
        "task_id": task_id,
        "status": "queued",
        "from_address": settlement.from_address,
        "to_address": to_address,
        "amount_usdc": amount_usdc,
    }


@router.get("/settlement/{task_id}/status")
async def get_settlement_status(task_id: str):
    """Get settlement status for a task."""
    if not _TASK_ID_PATTERN.match(task_id):
        raise HTTPException(status_code=400, detail="Invalid task_id format")
    from ..settlement.onchain import SettlementQueue
    from pathlib import Path

    queue = SettlementQueue(Path("./data/settlement"))
    pending = queue.get_pending()
    for s in pending:
        if s.task_id == task_id:
            return s.model_dump()

    raise HTTPException(status_code=404, detail="Settlement not found")


# --- Agent Execution with Event Broadcasting ---


@router.post("/tasks/{task_id}/full-lifecycle")
async def full_task_lifecycle(task_id: str, bid_amount: float, to_address: str):
    """Execute a full task lifecycle: bid -> execute -> settle.

    Bids on a task, executes it via AI, generates proof, and queues settlement.
    """
    if not _TASK_ID_PATTERN.match(task_id):
        raise HTTPException(status_code=400, detail="Invalid task_id format")
    if bid_amount <= 0 or bid_amount > 10000:
        raise HTTPException(status_code=400, detail="Bid amount must be between 0 and 10000 USDC")
    if not _ADDRESS_PATTERN.match(to_address):
        raise HTTPException(status_code=400, detail="Invalid Ethereum address format")
    # 1. Bid
    rep = _get_reputation()
    staker = _get_staker()
    stake = staker.stake_for_task(task_id, bid_amount)

    await event_bus.publish(Event(
        type="task_bid",
        task_id=task_id,
        data={"bid_amount": bid_amount, "stake": stake},
    ))

    # 2. Execute
    executor = WorkExecutor(timeout=300.0)
    task = Task(
        id=task_id,
        title=f"Task {task_id}",
        description="Full lifecycle execution",
        value_usdc=bid_amount,
        type="general",
        created_at=time.time(),
    )
    result = await executor.execute(task)

    await event_bus.publish(Event(
        type="task_completed",
        task_id=task_id,
        data={"success": result.success, "output": result.output[:200]},
    ))

    # 3. Settle
    from ..settlement.onchain import create_settler, SettlementQueue
    from pathlib import Path

    settler = create_settler()
    settlement = settler.create_settlement(task_id, to_address, bid_amount)
    queue = SettlementQueue(Path("./data/settlement"))
    queue.enqueue(settlement)

    # 4. Record in ledger
    ledger = _get_ledger()
    ledger.append(task_id, bid_amount, "credit", "Task completed")
    reclaimed = staker.execute_rate_and_claim(task_id)

    await event_bus.publish(Event(
        type="settlement_submitted",
        task_id=task_id,
        data={"amount": bid_amount, "to": to_address},
    ))

    return {
        "task_id": task_id,
        "bid": {"amount": bid_amount, "stake": stake},
        "execution": {
            "success": result.success,
            "output": result.output,
            "agent_type": result.agent_type.value,
        },
        "settlement": {
            "status": "queued",
            "to_address": to_address,
            "amount_usdc": bid_amount,
        },
        "ledger": {"reclaimed": reclaimed},
    }
