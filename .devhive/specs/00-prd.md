# Feature PRD: Full Clawforge Framework Build-Out

## 1. Problem Statement

AI agents currently lack a self-contained, autonomous runtime to participate in the Claw Earn marketplace. Operators must manually manage agent lifecycles, handle authentication, track earnings, and submit proofs — creating friction that prevents scalable agent deployment. There is no unified framework that combines wallet security, self-healing supervision, economic self-funding, and audit-grade reporting into a single deployable unit.

**This feature solves:** End-to-end autonomous agent operation on the Claw Earn marketplace with zero manual intervention after deployment.

## 2. Target Audience

- **Primary:** AI Agent Operators who want to deploy self-sustaining earning agents
- **Secondary:** Platform Operators managing Clawforge infrastructure
- **Tertiary:** Enterprise task submitters requiring audit-grade proof of work

## 3. Goals & Success Metrics

| Goal | Success Metric |
|------|---------------|
| Autonomous task lifecycle | Agent completes full cycle: discover → bid → execute → prove → settle without manual input |
| Self-healing reliability | Sentinel restarts failed agents within 60s; uptime ≥99.5% |
| Cryptographic security | All signatures use CLAW_V2 domain separation; zero key exposure incidents |
| Economic sustainability | Auto-staking at 10%; earnings offset operational costs within 30 days |
| Audit integrity | 100% of actions logged with tamper-evident hash chain |
| Enterprise readiness | RUNBOOK.md enables deployment by a new operator in <30 minutes |

## 4. Non-Goals (Out of Scope)

- No web UI or dashboard — CLI + REST API only
- No cloud key management (AWS KMS, HashiCorp Vault) — local env vars only
- No multi-tenant isolation — single operator model
- No cross-chain token bridging — USDC-only internal ledger
- No machine learning model training — agents use rule-based + heuristic logic
- No external database — all storage is file-based with tiered memory

## 5. User Experience & Flows

### Flow 1: Initial Deployment
```
1. Operator sets CLAW_EARN_WALLET and CLAW_EARN_PRIVATE_KEY env vars
2. Operator runs: docker-compose up -d
3. Sentinel starts, validates wallet signature with a test message
4. Protocol Loader fetches latest claw-earn.json
5. Agent enters IDLE state, begins scanning for tasks
```

### Flow 2: Task Lifecycle (Happy Path)
```
1. Task Discovery fetches /claw/tasks, filters FUNDED status
2. Smart Bidder evaluates task against reputation tier and cost model
3. Auto-start triggers for tasks <$100; manual review for higher value
4. Work Executor dispatches to specialized agent
5. Agent produces work, generates SHA-256/Keccak-256 proof
6. Proof submitted to marketplace API
7. Settlement statement generated and logged
8. Credits awarded, auto-stake 10%, remaining credited to balance
```

### Flow 3: Self-Healing (Failure Path)
```
1. Sentinel heartbeat detects agent unresponsive (>60s)
2. Sentinel logs failure with timestamp and context
3. Process supervisor restarts agent
4. Agent resumes from last known state (HOT memory)
5. If restart fails 3x → Dead Man's Switch triggers operator alert
6. If agent silent >5min → escalated alert + graceful shutdown
```

### Flow 4: Anti-Starvation (Low Inventory)
```
1. Supply/Demand Scanner detects <5 available funded tasks
2. System enters fallback mode
3. "Study Tasks" auto-generated from WARM memory lessons
4. Agent performs self-improvement work (pattern analysis, skill refinement)
5. When funded tasks return, agent seamlessly transitions back
```

### Flow 5: Audit Verification
```
1. Auditor requests settlement statement for date range
2. System retrieves signed logs from COLD memory
3. Hash chain verified from genesis to latest entry
4. Settlement statement produced with cryptographic proof
5. Auditor independently verifies signature against public wallet
```

### Edge Cases
| Scenario | Handling |
|----------|---------|
| Invalid private key | Refuse to start; log error; exit with code 1 |
| Heartbeat stuck in limbo | Dead Man's Switch forces full restart after 5min |
| Proof submission network failure | Retry 3x with exponential backoff; queue for later |
| Task value exceeds balance | Skip task; log insufficient funds; continue scanning |
| Memory tier overflow | Oldest entries pruned per 30-day policy |
| Concurrent bid on same task | Atomic file lock prevents double-bid |
| Untrusted URL redirect | Reject; log critical alert; pause until human approves |
| Spend limit exceeded | Block transaction; log violation; queue for human approval |
| Secret Vault decryption failure | Refuse to sign; log error; enter safe mode |

## 6. Acceptance Criteria

### Module 0: Protocol Loading
- [ ] Fetches claw-earn.json from configured URL on startup
- [ ] Parses SKILL.md and extracts task schema
- [ ] Version mismatch triggers warning log
- [ ] Network failure degrades gracefully to cached spec

### Module 0.1: Strict HTTPS Trust Boundary
- [ ] All external resource fetching enforces HTTPS-only connections
- [ ] Only accepts documentation, JSON schemas, or API specs from `https://aiagentstore.ai` and verified sub-paths
- [ ] Rejects any URL not starting with `https://aiagentstore.ai/`
- [ ] Rejects any URL that redirects to a non-Claw host
- [ ] Pauses and logs critical "Unverified External Host" alert if non-Claw host or unknown auth model is introduced
- [ ] Requests human approval before proceeding when trust boundary is violated

### Module 1: Wallet & Authentication
- [ ] Reads CLAW_EARN_WALLET and CLAW_EARN_PRIVATE_KEY from environment
- [ ] Signs messages using CLAW_V2 EIP-191 domain separation
- [ ] Private key never written to disk or transmitted over network
- [ ] Signature verification succeeds with known test vector

### Module 1.1: Least Privilege Credential Scopes
- [ ] Implements "Restricted Server Signer" architecture with scoped credentials
- [ ] Dedicated server signer wallet with strict transaction spend limits (max gas fee per tx, max USDC stake per day)
- [ ] Main CLAW_EARN_PRIVATE_KEY never directly accessible to runtime — encrypted at rest, decrypted in memory only via Secret Vault
- [ ] Transactions exceeding spend limit are automatically blocked, logged, and routed to human approval queue
- [ ] Spend limit violations trigger critical alert without executing the transaction

### Module 2: Sentinel
- [ ] Heartbeat emitted every 60s with timestamp
- [ ] Freshness check fails if heartbeat >90s old
- [ ] Process restarts within 60s of failure detection
- [ ] Dead Man's Switch triggers after 5min of silence
- [ ] Restart counter resets after 10min of healthy operation

### Module 3: Memory System
- [ ] HOT tier stores real-time operational state (current task, bid status)
- [ ] WARM tier stores lessons learned (bid success rates, task patterns)
- [ ] COLD tier stores identity (wallet address, reputation score, history)
- [ ] Auto-promotion: WARM→HOT when pattern accessed >5 times in 1hr
- [ ] Auto-demotion: HOT→WARM after 30min of inactivity
- [ ] 30-day prune removes expired entries from all tiers

### Module 4: Fuel Credits
- [ ] Ledger records all credit movements with timestamps
- [ ] Auto-stake deducts exactly 10% from every earning
- [ ] Cost offset calculates and deducts operational expenses
- [ ] Reputation tiers update based on cumulative earnings
- [ ] Ledger is append-only; no in-place edits

### Module 5: Task Discovery
- [ ] Connects to /claw/tasks API endpoint
- [ ] Filters tasks by FUNDED status
- [ ] Auto-starts bidding for tasks valued <$100
- [ ] Smart bid price calculated from reputation tier + base cost
- [ ] Concurrent access protected by file-level locks

### Module 6: Work Execution
- [ ] Dispatches to correct specialized agent based on task type
- [ ] Generates SHA-256 proof for standard tasks
- [ ] Generates Keccak-256 proof for on-chain tasks
- [ ] Supports A2A subtask delegation to peer agents
- [ ] Proof includes task ID, timestamp, output hash, agent signature

### Module 7: Audit Trails
- [ ] Every action logged to append-only log file
- [ ] Hash chain links each entry to previous (tamper-evident)
- [ ] Settlement statements generated per task completion
- [ ] Statements signed with agent's private key
- [ ] Logs retained for minimum 90 days

### Module 8: Dynamic Sourcing
- [ ] Supply/Demand Scanner polls task inventory every 5min
- [ ] Fallback Study Tasks generated when inventory <5
- [ ] Study Tasks utilize WARM memory for self-improvement
- [ ] Transition back to live tasks is seamless (<30s)

### Cross-Cutting
- [ ] RUNBOOK.md enables fresh operator deployment in <30min
- [ ] docker-compose.yml supports Tier 1 (local) and Tier 2 (cloud) deploy
- [ ] README.md articulates value proposition for each stakeholder
- [ ] Security audit covers OWASP Top 10, EIP-191, cryptographic primitives
- [ ] All Python code passes ruff lint and mypy type check

## 7. Deliverables

| Artifact | Description |
|----------|-------------|
| `RUNBOOK.md` | Operational deployment guide for new operators |
| `README.md` | Value proposition showcase and quickstart |
| `docker-compose.yml` | Tier 1 (local) and Tier 2 (cloud) deployment |
| Security Audit Report | OWASP, EIP-191, cryptographic review |
| `.devhive/specs/00-prd.md` | This document |
| `docs/PRODUCT_REQUIREMENTS.md` | Master PRD (updated) |

## 8. Dependencies

- Python 3.12+ runtime
- FastAPI + uvicorn
- eth_account (EIP-191 signing)
- web3.py (Keccak-256 hashing)
- APScheduler (heartbeat scheduling)
- Docker + Docker Compose (deployment)
- cryptography (AES-256-GCM for key encryption at rest)
- SSL/TLS verification for HTTPS Trust Boundary enforcement

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Private key compromise | Critical | Local-only storage, env vars, no disk write, encrypted at rest via Secret Vault |
| Marketplace API downtime | High | Graceful degradation, retry with backoff |
| Agent infinite loop | Medium | Sentinel watchdog, max execution timeout |
| Memory corruption | Medium | Hash-verified tier boundaries, periodic integrity checks |
| Economic manipulation | High | Append-only ledger, signed settlements, immutable logs |
| Unverified external host | Critical | HTTPS Trust Boundary enforces aiagentstore.ai only; unknown hosts trigger pause + human approval |
| Spend limit bypass | Critical | Server signer with hard caps; overflow blocked and routed to human queue |
