# Phase 03: Architecture

## Executive Summary

The Clawforge framework employs a **Hexagonal Architecture (Ports & Adapters)** pattern to separate domain logic from infrastructure, enabling testability and maintainability. The system is structured as a single-process FastAPI application with 10 modular components communicating through well-defined ports. File-based storage uses atomic writes with OS-level locking, while cryptographic operations leverage EIP-191 CLAW_V2 domain separation and AES-256-GCM key encryption at rest.

## Architecture Pattern

**Hexagonal Architecture (Ports & Adapters)** combined with **Domain-Driven Design** for bounded context separation.

### Rationale
- **Testability**: Domain logic isolated from infrastructure (file I/O, HTTP, crypto)
- **Modularity**: Each module defines ports (interfaces) and adapters (implementations)
- **Single Process**: FastAPI application with async/await for concurrent operations
- **Zero Dependencies**: File-based storage eliminates external database requirements
- **Security**: Clear boundaries between crypto operations and business logic

### Dependency Flow
```
Infrastructure → Adapters → Ports ← Domain Core
```
Dependencies point inward; domain core knows nothing about FastAPI, file systems, or external services.

## UX/UI & Design System

**CLI + REST API only** — No web UI. All interactions via:
- REST API endpoints (FastAPI with OpenAPI/Swagger)
- CLI commands for operator management
- Structured JSON responses for programmatic access

**API Design Principles:**
- RESTful resource modeling
- Consistent error responses with error codes
- API versioning via URL prefix (`/v1/`)
- CORS disabled (single-tenant, no browser clients)

## Components & Modules

### Core Domain Layer

1. **Protocol Loader (Module 0)**: Fetches and validates Claw Earn specifications
   - Ports: `IProtocolRepository`, `IProtocolValidator`
   - Adapters: `RemoteProtocolAdapter`, `CachedProtocolAdapter`

2. **HTTPS Trust Boundary (Module 0.1)**: Enforces secure external connections
   - Ports: `ITrustBoundary`, `IHttpValidator`
   - Adapters: `HttpsEnforcementAdapter`, `RedirectInterceptorAdapter`

3. **Wallet & Authentication (Module 1)**: EIP-191 CLAW_V2 signing
   - Ports: `ISigner`, `IAuthenticator`
   - Adapters: `EthAccountSignerAdapter`, `ClawV2DomainAdapter`

4. **Least Privilege Credentials (Module 1.1)**: Scoped signing with spend limits
   - Ports: `ICredentialManager`, `ISpendGuard`
   - Adapters: `ServerSignerAdapter`, `SpendLimitGuardAdapter`, `SecretVaultAdapter`

### Infrastructure Layer

5. **Sentinel (Module 2)**: Self-healing process supervision
   - Ports: `IHeartbeatMonitor`, `IProcessSupervisor`
   - Adapters: `APSchedulerHeartbeatAdapter`, `ProcessRestartAdapter`, `DeadMansSwitchAdapter`

6. **3-Tier Memory (Module 3)**: Adaptive memory system
   - Ports: `IMemoryStore`, `IMemoryPromoter`, `IMemoryDemoter`
   - Adapters: `HotMemoryAdapter`, `WarmMemoryAdapter`, `ColdMemoryAdapter`, `AutoPromotionAdapter`

7. **Fuel Credits (Module 4)**: USDC-pegged economy
   - Ports: `ILedger`, `IStakingEngine`, `IReputationTracker`
   - Adapters: `AppendOnlyLedgerAdapter`, `AutoStakeAdapter`, `ReputationTierAdapter`

8. **Task Discovery (Module 5)**: Marketplace integration
   - Ports: `ITaskRepository`, `IBidder`
   - Adapters: `ClawEarnApiAdapter`, `SmartBidderAdapter`, `FileLockAdapter`

9. **Work Execution (Module 6)**: Proof generation and dispatch
   - Ports: `IWorkExecutor`, `IProofGenerator`
   - Adapters: `SpecializedAgentDispatcherAdapter`, `Sha256ProofAdapter`, `Keccak256ProofAdapter`

10. **Audit Trails (Module 7)**: Tamper-evident logging
    - Ports: `IAuditLogger`, `IChainVerifier`, `ISettlementGenerator`
    - Adapters: `HashChainLoggerAdapter`, `ChainVerifierAdapter`, `SignedSettlementAdapter`

11. **Dynamic Sourcing (Module 8)**: Anti-starvation algorithm
    - Ports: `ISupplyDemandScanner`, `IStudyTaskGenerator`
    - Adapters: `MarketplaceScannerAdapter`, `FallbackStudyTaskAdapter`

### Cross-Cutting Modules

12. **Configuration**: Environment variable management
13. **API Gateway**: FastAPI application with REST endpoints
14. **File Storage**: Atomic writes with fcntl locking
15. **Crypto Services**: AES-256-GCM encryption, hashing utilities

## Data Architecture & Models

### Pydantic Schemas (API Contract)

```python
# Core Entities
class WalletAddress(BaseModel):
    address: str  # 0x-prefixed Ethereum address
    checksum: str  # EIP-55 checksum

class ReputationTier(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"

class TaskStatus(str, Enum):
    FUNDED = "funded"
    BIDDEN = "bitten"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class Task(BaseModel):
    id: str
    title: str
    description: str
    value_usdc: Decimal
    status: TaskStatus
    created_at: datetime
    deadline: Optional[datetime]
    required_skills: list[str]
    proof_type: Literal["sha256", "keccak256"]

class Bid(BaseModel):
    task_id: str
    bid_amount: Decimal
    estimated_completion: datetime
    signature: str  # CLAW_V2 signed bid

class Proof(BaseModel):
    task_id: str
    output_hash: str  # SHA-256 or Keccak-256
    timestamp: datetime
    agent_signature: str
    metadata: dict[str, Any]

class SettlementStatement(BaseModel):
    task_id: str
    earnings: Decimal
    stake_amount: Decimal
    net_credit: Decimal
    timestamp: datetime
    agent_signature: str
    audit_chain_hash: str

class AuditEntry(BaseModel):
    index: int
    timestamp: datetime
    action: str
    actor: str
    payload: dict[str, Any]
    previous_hash: str
    entry_hash: str  # SHA-256 of (previous_hash + timestamp + action + payload)

class MemoryEntry(BaseModel):
    id: str
    tier: Literal["hot", "warm", "cold"]
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int
    tags: list[str]

class SpendLimit(BaseModel):
    max_gas_per_tx: Decimal
    max_usdc_stake_per_day: Decimal
    current_daily_stake: Decimal
    last_reset: datetime

class Heartbeat(BaseModel):
    timestamp: datetime
    status: Literal["healthy", "degraded", "failed"]
    agent_pid: int
    uptime_seconds: int
```

### File Storage Layout

```
/data/
├── protocol/
│   ├── claw-earn.json          # Current protocol spec
│   ├── claw-earn.json.bak      # Previous version backup
│   └── version.txt             # Current version hash
├── memory/
│   ├── hot/                    # Real-time operational state
│   │   ├── current_task.json
│   │   ├── bid_status.json
│   │   └── runtime_state.json
│   ├── warm/                   # Lessons learned
│   │   ├── patterns.jsonl      # Append-only pattern log
│   │   ├── success_rates.json
│   │   └── lessons_learned.json
│   └── cold/                   # Identity & long-term
│       ├── wallet.json         # Public wallet info (NEVER private key)
│       ├── reputation.json
│       └── history.jsonl       # Complete action history
├── economy/
│   ├── ledger.jsonl            # Append-only USDC ledger
│   ├── staking.json            # Current stake position
│   └── reputation.json         # Reputation tier & score
├── tasks/
│   ├── active/                 # Currently active tasks
│   │   └── {task_id}.json
│   ├── completed/              # Finished tasks
│   │   └── {task_id}.json
│   ├── bids/                   # Bid records
│   │   └── {task_id}_bid.json
│   └── inventory.json          # Current task inventory cache
├── audit/
│   ├── chain.jsonl             # Append-only hash-chained logs
│   ├── settlements/            # Signed settlement statements
│   │   └── {task_id}_settlement.json
│   └── backups/                # Pruned log archives
│       └── chain_YYYYMMDD.jsonl.gz
├── credentials/
│   ├── server_signer.json      # Server signer wallet (public only)
│   ├── spend_limits.json       # Current spend limits
│   └── approval_queue.json     # Pending human approvals
├── sentinel/
│   ├── heartbeat.json          # Latest heartbeat state
│   ├── restart_count.json      # Restart counter
│   └── dead_mans_switch.json   # DMS state
└── config/
    └── runtime.json            # Runtime configuration snapshot
```

### Storage Patterns

**Atomic Writes (temp + rename):**
```python
async def atomic_write(path: Path, data: bytes) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        temp_path.write_bytes(data)
        temp_path.rename(path)  # Atomic on same filesystem
    finally:
        temp_path.unlink(missing_ok=True)
```

**File Locking (fcntl):**
```python
import fcntl

async def locked_write(path: Path, data: bytes) -> None:
    with open(path, 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(data)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
```

## APIs / Interfaces

### REST API Endpoints

**Health & Status:**
- `GET /v1/health` → `{"status": "healthy", "uptime": 12345}`
- `GET /v1/status` → Agent state, memory tier stats, economy summary
- `GET /v1/sentinel/heartbeat` → Latest heartbeat data

**Task Management:**
- `GET /v1/tasks` → List discovered tasks with filters
- `GET /v1/tasks/{task_id}` → Task details
- `POST /v1/tasks/{task_id}/bid` → Submit bid for task
- `GET /v1/tasks/{task_id}/proof` → Retrieve task proof

**Economy:**
- `GET /v1/economy/balance` → Current USDC balance
- `GET /v1/economy/staking` → Staking position
- `GET /v1/economy/reputation` → Reputation tier & score
- `GET /v1/economy/ledger?limit=100` → Recent ledger entries

**Audit & Compliance:**
- `GET /v1/audit/logs?since=2026-01-01` → Audit logs with hash chain
- `GET /v1/audit/settlements/{task_id}` → Signed settlement statement
- `POST /v1/audit/verify` → Verify hash chain integrity

**Memory:**
- `GET /v1/memory/{tier}` → Memory entries by tier (hot/warm/cold)
- `GET /v1/memory/stats` → Memory tier statistics

**Sentinel:**
- `POST /v1/sentinel/restart` → Manual restart trigger
- `GET /v1/sentinel/status` → Sentinel health & restart count

**Configuration:**
- `GET /v1/config` → Current runtime configuration
- `PUT /v1/config/limits` → Update spend limits (requires approval)

### Internal Port Interfaces

```python
# Example Port Interface
class ISigner(Protocol):
    @abstractmethod
    async def sign_message(self, message: str) -> str:
        """Sign message with CLAW_V2 domain separation."""
        pass

    @abstractmethod
    async def verify_signature(self, message: str, signature: str) -> bool:
        """Verify CLAW_V2 signature against public key."""
        pass

class ITaskRepository(Protocol):
    @abstractmethod
    async def fetch_funded_tasks(self) -> list[Task]:
        """Fetch tasks with FUNDED status from marketplace."""
        pass

    @abstractmethod
    async def save_bid(self, bid: Bid) -> None:
        """Persist bid with file locking."""
        pass
```

## Component Interaction Diagrams

### Task Lifecycle Flow

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Task      │    │   Smart      │    │    Work      │    │   Proof      │
│  Discovery  │───▶│   Bidder     │───▶│  Executor    │───▶│  Generator   │
│  (Module 5) │    │  (Module 5)  │    │  (Module 6)  │    │  (Module 6)  │
└─────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │                  │                   │                   │
       ▼                  ▼                   ▼                   ▼
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Memory    │    │   Fuel       │    │    Audit     │    │  Settlement  │
│   (Module 3)│    │  Credits (4) │    │  Trails (7)  │    │  Generator   │
└─────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

### Self-Healing Flow

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│  Sentinel   │───▶│  Heartbeat   │───▶│  Dead Man's  │
│  (Module 2) │    │  Monitor     │    │  Switch      │
└─────────────┘    └──────────────┘    └──────────────┘
       │                  │                   │
       ▼                  ▼                   ▼
┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│   Process   │    │   Failure    │    │   Operator   │
│  Supervisor │    │  Detection   │    │    Alert     │
└─────────────┘    └──────────────┘    └──────────────┘
```

### Security Boundary Flow

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│  Protocol   │───▶│   HTTPS      │───▶│   Trust      │
│  Loader (0) │    │  Boundary    │    │  Validator   │
└─────────────┘    │  (Module 0.1)│    │              │
                   └──────────────┘    └──────────────┘
                          │                   │
                          ▼                   ▼
                   ┌──────────────┐    ┌──────────────┐
                   │   Redirect   │    │   Human      │
                   │  Interceptor │    │   Approval   │
                   └──────────────┘    └──────────────┘
```

## Security Architecture

### Zero-Trust Model

**Principle:** Every operation must be cryptographically verified; no implicit trust.

**Implementation Layers:**

1. **Identity Verification**
   - EIP-191 CLAW_V2 domain-separated signing
   - Wallet address as unique agent identity
   - No shared secrets; each agent has unique keypair

2. **Access Control**
   - Least-privilege credential scoping
   - Server signer wallet with hard spend limits
   - Main private key encrypted at rest via Secret Vault
   - Human-in-the-loop for limit violations

3. **Data Integrity**
   - Hash-chained append-only audit logs
   - SHA-256/Keccak-256 proof generation
   - Signed settlement statements
   - Tamper-evident file storage

4. **Network Security**
   - HTTPS-only external connections
   - Trust boundary enforcement (`https://aiagentstore.ai/` only)
   - Redirect interception and validation
   - No cloud KMS; local key management only

5. **Cryptographic Operations**
   - AES-256-GCM for key encryption at rest
   - EIP-191 message signing format
   - Keccak-256 for on-chain proofs
   - SHA-256 for off-chain proofs

### Key Management Flow

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│  Environment│───▶│   Secret     │───▶│   In-Memory   │
│  Variables  │    │   Vault      │    │   Decrypted   │
└─────────────┘    │  (AES-256)   │    │    Key       │
                   └──────────────┘    └──────────────┘
                          │                   │
                          ▼                   ▼
                   ┌──────────────┐    ┌──────────────┐
                   │   Encrypted  │    │  Signing     │
                   │   at Rest    │    │  Operation   │
                   └──────────────┘    └──────────────┘
```

### Trust Boundary Rules

1. **URL Validation**: All external URLs must start with `https://aiagentstore.ai/`
2. **Redirect Interception**: HTTP redirects to non-Claw hosts are blocked
3. **Human Approval**: Trust boundary violations pause execution pending approval
4. **Logging**: All external requests logged with full URL and response status

### Spend Limit Enforcement

1. **Server Signer**: Dedicated wallet with hard caps
2. **Per-Transaction Limit**: Maximum gas fee per transaction
3. **Daily Limit**: Maximum USDC stake per 24-hour period
4. **Violation Handling**: Automatic block, critical alert, human approval queue

## Infrastructure & Deployment

### Docker Compose Architecture

**Tier 1 (Local Development):**
```yaml
services:
  clawforge:
    build: .
    volumes:
      - ./data:/app/data
    environment:
      - CLAW_EARN_WALLET=${CLAW_EARN_WALLET}
      - CLAW_EARN_PRIVATE_KEY=${CLAW_EARN_PRIVATE_KEY}
      - CLAW_VAULT_KEY=${CLAW_VAULT_KEY}
    ports:
      - "8000:8000"
```

**Tier 2 (Cloud Deployment):**
```yaml
services:
  clawforge:
    build: .
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
    volumes:
      - clawforge-data:/app/data
    environment:
      - CLAW_EARN_WALLET=${CLAW_EARN_WALLET}
      - CLAW_EARN_PRIVATE_KEY=${CLAW_EARN_PRIVATE_KEY}
      - CLAW_VAULT_KEY=${CLAW_VAULT_KEY}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Multi-Stage Docker Build

```dockerfile
# Build stage
FROM python:3.12-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY src/ ./src/
EXPOSE 8000
CMD ["uvicorn", "src.clawforge.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Deployment Requirements

**Minimum System:**
- 2 CPU cores
- 4GB RAM
- 20GB disk (grows with audit logs)
- Python 3.12+
- Linux (Docker required)

**Environment Variables:**
- `CLAW_EARN_WALLET`: Agent wallet address (0x-prefixed)
- `CLAW_EARN_PRIVATE_KEY`: Encrypted private key (AES-256-GCM)
- `CLAW_VAULT_KEY`: Vault decryption key (32 bytes)
- `CLAW_API_BASE_URL`: Marketplace API endpoint (default: `https://aiagentstore.ai`)

### Monitoring & Observability

**Logging:**
- Structured JSON logs via `structlog`
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- All external requests logged with full context
- Audit logs append-only with hash chain

**Metrics:**
- Heartbeat freshness (seconds since last beat)
- Task completion rate (%)
- Proof verification success rate (%)
- Memory tier sizes (entries per tier)
- Ledger balance (USDC)
- Restart count (sentinel)

**Alerting:**
- Heartbeat stale (>90s): Warning
- Dead Man's Switch (5min silence): Critical
- Spend limit violation: Critical
- Trust boundary violation: Critical
- Hash chain corruption: Critical

### Backup & Recovery

**Daily Backup:**
- Compress audit logs older than 30 days
- Archive to `/data/audit/backups/`
- Retain backups for 90 days minimum

**Recovery Procedures:**
1. **Memory Corruption**: Restore from last known good state
2. **Ledger Corruption**: Rebuild from audit log hash chain
3. **Sentinel Failure**: Process supervisor auto-restarts
4. **Key Compromise**: Rotate vault key, re-encrypt all secrets