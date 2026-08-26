# Product Requirements Document (Master PRD)

## Dutchkem Ventures Clawforge

**Version:** 1.0.0
**Date:** 2026-08-26
**Status:** Draft

---

## 1. Project Vision

Dutchkem Ventures Clawforge is an **Autonomous Claw Earn Marketplace Integration Framework** — a self-healing, self-funding runtime that enables AI agents to autonomously discover, claim, deliver, and earn from tasks on the Claw Earn marketplace. The system operates on zero-trust principles with wallet-based authentication, internal fuel credit economy, and enterprise-grade audit trails.

## 2. Target Audience

| Persona | Description |
|---------|-------------|
| **AI Agent Operators** | Deploy autonomous agents that earn revenue by completing marketplace tasks |
| **Platform Operators** | Run the Clawforge runtime infrastructure, manage wallets and economic parameters |
| **Enterprise Clients** | Submit tasks to the marketplace, receive audit-grade proofs of completion |
| **Security Auditors** | Verify cryptographic integrity, audit trail immutability, and zero-trust compliance |

## 3. Core Features

### 3.1 Protocol Loading (Module 0)
- Fetch live Claw Earn specification from official URLs
- Parse `SKILL.md` and `claw-earn.json` at runtime
- Version-aware protocol synchronization

### 3.1.1 Strict HTTPS Trust Boundary (Module 0.1)
- Enforce HTTPS-only connections for all external resource fetching
- Accept documentation, schemas, or API specs exclusively from `https://aiagentstore.ai` and verified sub-paths
- Reject URLs not starting with `https://aiagentstore.ai/` or that redirect to non-Claw hosts
- Pause and log critical "Unverified External Host" alert when trust boundary is violated
- Require human approval before proceeding with unverified external resources

### 3.2 Wallet & Authentication (Module 1)
- CLAW_EARN_WALLET / CLAW_EARN_PRIVATE_KEY environment variables
- EIP-191 domain-separated message signing (CLAW_V2)
- Local-only private key storage — zero network exposure

### 3.2.1 Least Privilege Credential Scopes (Module 1.1)
- "Restricted Server Signer" architecture with scoped credentials
- Dedicated server signer wallet with strict spend limits (max gas per tx, max USDC stake per day)
- Main CLAW_EARN_PRIVATE_KEY encrypted at rest, decrypted in memory only via Secret Vault for exact signed transaction
- Transactions exceeding spend limit are automatically blocked, logged, and routed to human approval queue
- Spend limit violations trigger critical alert without transaction execution

### 3.3 Sentinel Self-Healing Runtime (Module 2)
- Process supervisor with automatic restart
- Heartbeat monitoring (60s intervals, ≤90s freshness)
- Dead Man's Switch (>5min silence triggers escalation)

### 3.4 3-Tier Adaptive Memory (Module 3)
- HOT tier: real-time operational state
- WARM tier: lessons learned and patterns
- COLD tier: agent identity and long-term knowledge
- Auto-promotion/demotion rules, 30-day prune cycle

### 3.5 Fuel Credit Economy (Module 4)
- Internal ledger pegged 1:1 USDC
- Auto-staking (10% of earnings)
- Operational cost offset mechanism
- Reputation tiers (Bronze → Diamond)

### 3.6 Task Discovery & Bidding (Module 5)
- API client for `/claw/tasks` endpoint
- FUNDED status filter, auto-start for tasks <$100
- Smart bidding with reputation-weighted pricing

### 3.7 Work Execution & Proof (Module 6)
- Specialized agent dispatch per task type
- SHA-256 / Keccak-256 proof generation
- Agent-to-Agent (A2A) subtask outsourcing

### 3.8 Audit Trails & Reporting (Module 7)
- Signed settlement statements
- Immutable append-only logs
- Tamper-evident hash chaining

### 3.9 Dynamic Task Sourcing (Module 8)
- Supply/Demand Scanner for marketplace conditions
- Fallback "Study Tasks" when inventory is low
- Anti-starvation algorithm

## 4. Key User Flows

```
Flow 1: Task Lifecycle
  Agent → Discovery → Bid → Accept → Execute → Proof → Settlement

Flow 2: Self-Healing
  Sentinel → Heartbeat Check → Failure Detected → Restart → Resume

Flow 3: Economic Cycle
  Earn Credits → Auto-Stake → Offset Costs → Reinvest → Scale

Flow 4: Audit
  Action → Log → Hash Chain → Settlement Statement → Verification
```

## 5. Technology Stack

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.12+, asyncio |
| Web Framework | FastAPI |
| Crypto | eth_account, web3.py, EIP-191 |
| Scheduling | APScheduler |
| Storage | File-based (no external DB) |
| Auth | CLAW_V2 domain-separated signing |
| Deployment | Docker Compose (Tier 1/2) |

## 6. Security Model

- **Zero-Trust:** All operations verified via cryptographic signatures
- **Local-Only Keys:** Private keys never leave the host machine
- **Immutable Logs:** Append-only, hash-chained audit trail
- **Domain Separation:** EIP-191 CLAW_V2 prevents cross-protocol replay
- **HTTPS Trust Boundary:** All external fetches restricted to `https://aiagentstore.ai` only
- **Least Privilege Signing:** Server signer wallet with hard spend limits; master key encrypted at rest via Secret Vault
- **Human-in-the-Loop:** Trust boundary violations and spend limit overflows require explicit human approval

## 7. Non-Goals (Initial Release)

- No centralized database dependency
- No cloud-hosted key management (HSM/KMS)
- No cross-chain bridging
- No UI dashboard (CLI + API only)
- No multi-tenancy isolation (single operator model)

## 8. Success Metrics

| Metric | Target |
|--------|--------|
| Agent uptime | ≥99.5% with Sentinel |
| Task completion rate | ≥90% |
| Proof verification pass rate | 100% |
| Heartbeat freshness | ≤90s at all times |
| Audit log integrity | Zero tamper incidents |
| Auto-stake compliance | 10% of every earning |
| Trust boundary violations | Zero unapproved external fetches |
| Spend limit breaches | Zero unauthorized overages |
