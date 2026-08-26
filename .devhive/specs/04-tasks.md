# Phase 04: Task Plan

## Executive Summary
Build a complete autonomous AI agent runtime for the Claw Earn marketplace with 10 modules, file-based storage, Docker deployment, and comprehensive security. The execution follows a bottom-up approach: infrastructure setup, data schemas, backend module implementation, performance testing, and documentation.

## Design Tasks
*None required*

## Infrastructure Tasks
- [ ] **Task 1: Multi-Stage Dockerfile**
  - Description: Create Dockerfile with builder and runtime stages using python:3.12-slim base images. Install dependencies in builder, copy only production artifacts to runtime.
  - Files: `Dockerfile`
  - Skills: docker-expert

- [ ] **Task 2: Docker Compose Configuration**
  - Description: Create docker-compose.yml with Tier 1 (local) and Tier 2 (cloud) service configurations, including volume mounts, environment variables, resource limits, and healthchecks.
  - Files: `docker-compose.yml`, `.env.example`
  - Skills: docker-expert

- [ ] **Task 3: CI/CD Pipeline Setup**
  - Description: Configure GitHub Actions workflow for linting (ruff), type checking (mypy --strict), testing, and Docker image build/push.
  - Files: `.github/workflows/ci.yml`
  - Skills: devops, docker-expert

- [ ] **Task 4: Environment Variable Template**
  - Description: Create .env.example with all required environment variables documented, including CLAW_EARN_WALLET, CLAW_EARN_PRIVATE_KEY, CLAW_VAULT_KEY, and CLAW_API_BASE_URL.
  - Files: `.env.example`
  - Skills: None

## Data Tasks
- [ ] **Task 1: Pydantic Schema Definitions**
  - Description: Define all Pydantic models from architecture: WalletAddress, ReputationTier, TaskStatus, Task, Bid, Proof, SettlementStatement, AuditEntry, MemoryEntry, SpendLimit, Heartbeat.
  - Files: `src/clawforge/schemas.py`
  - Skills: backend-architect

- [ ] **Task 2: File Storage Directory Structure**
  - Description: Create initial directory structure under /data/ for protocol, memory (hot/warm/cold), economy, tasks, audit, credentials, sentinel, and config.
  - Files: `src/clawforge/storage/paths.py`
  - Skills: backend-architect

- [ ] **Task 3: Atomic Write and File Locking Utilities**
  - Description: Implement atomic_write() and locked_write() utility functions using temp+rename pattern and fcntl locking.
  - Files: `src/clawforge/storage/atomic.py`, `src/clawforge/storage/locking.py`
  - Skills: backend-architect, backend-security-coder

## Backend Tasks
- [ ] **Task 1: Project Structure Setup**
  - Description: Initialize Python package structure with src/clawforge/ layout, __init__.py files, pyproject.toml with dependencies (eth_account, web3.py, cryptography, APScheduler, httpx, fastapi, uvicorn, structlog, pydantic).
  - Files: `pyproject.toml`, `src/clawforge/__init__.py`, `src/clawforge/config.py`
  - Skills: backend-architect

- [ ] **Task 2: Configuration Module**
  - Description: Implement config.py to load environment variables (CLAW_EARN_WALLET, CLAW_EARN_PRIVATE_KEY, CLAW_VAULT_KEY, CLAW_API_BASE_URL) with validation and type conversion.
  - Files: `src/clawforge/config.py`
  - Skills: backend-security-coder

- [ ] **Task 3: Module 0 - Protocol Loading**
  - Description: Implement IProtocolRepository and IProtocolValidator ports with RemoteProtocolAdapter and CachedProtocolAdapter. Fetch claw-earn.json, parse spec, handle network failures gracefully.
  - Files: `src/clawforge/protocol/loader.py`, `src/clawforge/protocol/trust.py`
  - Skills: backend-architect, backend-security-coder

- [ ] **Task 4: Module 0.1 - HTTPS Trust Boundary**
  - Description: Implement ITrustBoundary and IHttpValidator ports with HttpsEnforcementAdapter and RedirectInterceptorAdapter. Validate all URLs start with https://aiagentstore.ai/, intercept redirects, block non-Claw hosts.
  - Files: `src/clawforge/protocol/trust.py`, `src/clawforge/protocol/validator.py`
  - Skills: backend-security-coder

- [ ] **Task 5: Module 1 - Wallet & Authentication**
  - Description: Implement ISigner and IAuthenticator ports with EthAccountSignerAdapter and ClawV2DomainAdapter. EIP-191 CLAW_V2 domain-separated signing, never expose private key.
  - Files: `src/clawforge/crypto/signing.py`, `src/clawforge/crypto/hashing.py`
  - Skills: backend-security-coder

- [ ] **Task 6: Module 1.1 - Least Privilege Credentials**
  - Description: Implement ICredentialManager and ISpendGuard ports with ServerSignerAdapter, SpendLimitGuardAdapter, and SecretVaultAdapter. Server signer with spend limits, AES-256-GCM key encryption, human approval queue.
  - Files: `src/clawforge/credentials/server_signer.py`, `src/clawforge/credentials/approval.py`, `src/clawforge/crypto/vault.py`
  - Skills: backend-security-coder

- [ ] **Task 7: Module 2 - Sentinel**
  - Description: Implement IHeartbeatMonitor and IProcessSupervisor ports with APSchedulerHeartbeatAdapter, ProcessRestartAdapter, and DeadMansSwitchAdapter. 60s heartbeat, 90s freshness, 5min DMS, process restart.
  - Files: `src/clawforge/sentinel/heartbeat.py`, `src/clawforge/sentinel/watchdog.py`
  - Skills: backend-architect

- [ ] **Task 8: Module 3 - Memory System**
  - Description: Implement IMemoryStore, IMemoryPromoter, IMemoryDemoter ports with HotMemoryAdapter, WarmMemoryAdapter, ColdMemoryAdapter, AutoPromotionAdapter. HOT/WARM/COLD tiers, auto-promote (>5 accesses/hr), auto-demote (30min idle), 30-day prune.
  - Files: `src/clawforge/memory/tier.py`, `src/clawforge/memory/promotion.py`, `src/clawforge/memory/prune.py`
  - Skills: backend-architect

- [ ] **Task 9: Module 4 - Fuel Credits**
  - Description: Implement ILedger, IStakingEngine, IReputationTracker ports with AppendOnlyLedgerAdapter, AutoStakeAdapter, ReputationTierAdapter. Append-only USDC ledger, 10% auto-stake, cost offset, reputation tiers.
  - Files: `src/clawforge/economy/ledger.py`, `src/clawforge/economy/staking.py`, `src/clawforge/economy/reputation.py`
  - Skills: backend-architect

- [ ] **Task 10: Module 5 - Task Discovery**
  - Description: Implement ITaskRepository and IBidder ports with ClawEarnApiAdapter, SmartBidderAdapter, FileLockAdapter. Connect to /claw/tasks, filter FUNDED, auto-start <$100, smart bidding.
  - Files: `src/clawforge/tasks/discovery.py`, `src/clawforge/tasks/bidder.py`
  - Skills: backend-architect

- [ ] **Task 11: Module 6 - Work Execution**
  - Description: Implement IWorkExecutor and IProofGenerator ports with SpecializedAgentDispatcherAdapter, Sha256ProofAdapter, Keccak256ProofAdapter. Dispatch to agents, generate SHA-256/Keccak-256 proofs, A2A subtask delegation.
  - Files: `src/clawforge/tasks/executor.py`, `src/clawforge/tasks/proof.py`
  - Skills: backend-architect

- [ ] **Task 12: Module 7 - Audit Trails**
  - Description: Implement IAuditLogger, IChainVerifier, ISettlementGenerator ports with HashChainLoggerAdapter, ChainVerifierAdapter, SignedSettlementAdapter. Hash-chained append-only logs, chain verification, signed settlements.
  - Files: `src/clawforge/audit/logger.py`, `src/clawforge/audit/chain.py`, `src/clawforge/audit/settlement.py`
  - Skills: backend-architect

- [ ] **Task 13: Module 8 - Dynamic Sourcing**
  - Description: Implement ISupplyDemandScanner and IStudyTaskGenerator ports with MarketplaceScannerAdapter, FallbackStudyTaskAdapter. Poll inventory every 5min, generate study tasks when <5, seamless transition.
  - Files: `src/clawforge/tasks/sourcing.py`
  - Skills: backend-architect

- [ ] **Task 14: FastAPI Application & REST Endpoints**
  - Description: Create main.py with FastAPI app, implement all REST endpoints: /v1/health, /v1/status, /v1/tasks, /v1/economy, /v1/audit, /v1/memory, /v1/sentinel, /v1/config.
  - Files: `src/clawforge/main.py`, `src/clawforge/api/routes.py`
  - Skills: backend-architect

- [ ] **Task 15: Integration Test Suite**
  - Description: Write comprehensive integration tests for all modules, covering happy paths, failure modes, and edge cases. Include EIP-191 test vectors, file locking concurrency, hash chain verification.
  - Files: `tests/`, `tests/conftest.py`
  - Skills: devhive-qa

## Frontend Tasks
*None required*

## Performance Tasks
- [ ] **Task 1: API Load Testing**
  - Description: Create k6 or artillery load test scripts for critical API endpoints: /v1/health, /v1/tasks, /v1/economy/balance. Measure latency, throughput, and error rates under concurrent load.
  - Files: `tests/performance/load_test.js`
  - Skills: devhive-perf

- [ ] **Task 2: File Locking Stress Test**
  - Description: Write stress tests for concurrent file access patterns: multiple writers to ledger, simultaneous memory tier promotions, parallel bid submissions. Verify data integrity under contention.
  - Files: `tests/performance/concurrency_test.py`
  - Skills: devhive-perf

## Documentation Tasks
- [x] **Task 1: RUNBOOK.md Creation**
  - Description: Write operational deployment guide covering prerequisites, environment setup, Docker deployment, monitoring, troubleshooting, and recovery procedures. Target: fresh operator deployment in <30 minutes.
  - Files: `RUNBOOK.md`
  - Skills: devhive-techwriter

- [ ] **Task 2: README.md Creation**
  - Description: Write project README with value proposition for each stakeholder (operators, platform operators, enterprise submitters), quickstart guide, architecture overview, and module descriptions.
  - Files: `README.md`
  - Skills: devhive-techwriter

- [ ] **Task 3: API Documentation**
  - Description: Ensure FastAPI auto-generates OpenAPI/Swagger docs. Add detailed docstrings to all endpoints and Pydantic models for comprehensive API documentation.
  - Files: `src/clawforge/main.py`, `src/clawforge/api/routes.py`
  - Skills: devhive-techwriter

- [ ] **Task 4: Security Audit Report**
  - Description: Create security audit document covering OWASP Top 10 mitigations, EIP-191 compliance verification, cryptographic primitive review, trust boundary enforcement, and spend limit enforcement.
  - Files: `docs/SECURITY_AUDIT.md`
  - Skills: backend-security-coder, devhive-techwriter

## Release Tasks
- [ ] **Task 1: Version & Changelog Setup**
  - Description: Configure semantic versioning in pyproject.toml, create initial CHANGELOG.md following Keep a Changelog format.
  - Files: `pyproject.toml`, `CHANGELOG.md`
  - Skills: devhive-releaser

- [ ] **Task 2: Local Git Tag Creation**
  - Description: Create initial git tag v0.1.0 after first successful build and test pass.
  - Files: None
  - Skills: devhive-releaser