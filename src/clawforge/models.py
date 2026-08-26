"""All Pydantic data models for the Clawforge framework."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ReputationTier(str, Enum):
    """Reputation tier for agents."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


class TaskStatus(str, Enum):
    """Status of a task in the marketplace."""

    FUNDED = "funded"
    BIDDEN = "bitten"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class WalletAddress(BaseModel):
    """Ethereum wallet address with checksum."""

    address: str = Field(..., pattern=r"^0x[0-9a-fA-F]{40}$")
    checksum: str = Field(..., pattern=r"^0x[0-9a-fA-F]{40}$")


class Task(BaseModel):
    """Task from the Claw Earn marketplace."""

    id: str
    title: str
    description: str
    value_usdc: float
    status: str = "FUNDED"
    type: str = "general"
    created_at: float = 0.0
    deadline: Optional[float] = None
    required_skills: list[str] = Field(default_factory=list)
    proof_type: Literal["sha256", "keccak256"] = "sha256"


class Bid(BaseModel):
    """Bid submitted for a task."""

    task_id: str
    bid_amount: float
    estimated_completion: float = 0.0
    signature: str = Field(..., description="CLAW_V2 signed bid")


class Proof(BaseModel):
    """Proof of work submission."""

    task_id: str
    output_hash: str
    timestamp: float
    agent_signature: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class LedgerEntry(BaseModel):
    """Single ledger entry for USDC transactions."""

    timestamp: float
    task_id: str
    amount: float
    type: str
    description: str = ""
    prev_hash: str = "genesis"
    hash: str = ""


class StakeRecord(BaseModel):
    """Record of a staked amount for a task."""

    task_id: str
    amount: float
    staked_at: float
    status: str = "staked"
    reclaimed_at: Optional[float] = None


class ReputationProfile(BaseModel):
    """Agent reputation profile."""

    total_ratings: int = 0
    rating_sum: float = 0.0
    average_rating: float = 0.0
    tier: str = "bronze"
    stake_percentage: float = 0.30


class TaskFilter(BaseModel):
    """Filter criteria for task discovery."""

    status: str = "FUNDED"
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    required_skills: list[str] = Field(default_factory=list)


class AgentType(str, Enum):
    """Specialized agent types for task dispatch."""

    SALES = "sales"
    KYC_AML = "kyc"
    ECOMMERCE = "ecommerce"
    GENERAL = "general"


class TaskResult(BaseModel):
    """Result of task execution."""

    task_id: str
    success: bool
    output: str
    execution_time: float
    error: Optional[str] = None
    agent_type: AgentType = AgentType.GENERAL


class Subtask(BaseModel):
    """A2A subtask for peer agent delegation."""

    id: str
    description: str
    type: str
    value_usdc: float
    created_at: float


class AuditEntry(BaseModel):
    """Hash-chained audit log entry."""

    timestamp: float
    action: str
    task_id: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    prev_hash: str = "genesis"
    hash: str = ""


class StateTransition(BaseModel):
    """State transition in a settlement statement."""

    from_state: str
    to_state: str
    timestamp: float
    reason: str = ""


class SettlementStatement(BaseModel):
    """Signed settlement statement for completed task."""

    task_id: str
    agent_address: str
    transitions: list[StateTransition] = Field(default_factory=list)
    total_amount: float = 0.0
    generated_at: float = 0.0
    signature: str = ""


class SpendLimit(BaseModel):
    """Spend limit configuration for server signer."""

    max_gas_per_tx: float
    max_usdc_stake_per_day: float
    current_daily_stake: float = 0.0
    last_reset: float = 0.0


class Heartbeat(BaseModel):
    """Sentinel heartbeat status."""

    timestamp: float = 0.0
    status: Literal["healthy", "degraded", "failed"] = "healthy"
    agent_pid: int = 0
    uptime_seconds: int = 0


class ProtocolSpec(BaseModel):
    """Claw Earn protocol specification."""

    version: str
    endpoints: dict[str, str]
    schemas: dict[str, Any]
    skills: list[str] = Field(default_factory=list)


class AgentIdentity(BaseModel):
    """Agent identity information."""

    wallet_address: str
    reputation_tier: str = "bronze"
    reputation_score: float = 0.0
    total_earnings: float = 0.0
    total_staked: float = 0.0


class TaskInventory(BaseModel):
    """Task inventory cache."""

    tasks: list[Task] = Field(default_factory=list)
    last_fetched: float = 0.0
    count: int = 0


class StakingPosition(BaseModel):
    """Current staking position."""

    total_staked: float = 0.0
    active_stakes: dict[str, float] = Field(default_factory=dict)
    reclaimed: float = 0.0


class ApprovalRequest(BaseModel):
    """Request for human approval."""

    id: str
    timestamp: float = 0.0
    action: str
    details: dict[str, Any]
    status: Literal["pending", "approved", "rejected"] = "pending"


class SentinelState(BaseModel):
    """Sentinel operational state."""

    heartbeat: Optional[Heartbeat] = None
    restart_count: int = 0
    last_restart: Optional[float] = None
    dead_mans_switch_active: bool = False


class MemoryEntry(BaseModel):
    """Memory entry in tiered storage."""

    id: str
    tier: Literal["hot", "warm", "cold"]
    key: str
    value: Any
    created_at: float = 0.0
    last_accessed: float = 0.0
    access_count: int = 0
    tags: list[str] = Field(default_factory=list)
