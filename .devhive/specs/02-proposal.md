# Phase 02: Proposal

## Executive Summary
Build a complete autonomous AI agent runtime for the Claw Earn marketplace that combines cryptographic wallet authentication (EIP-191 CLAW_V2), self-healing process supervision, tiered memory, internal USDC economy, and tamper-evident audit trails into a single Docker-deployable unit with zero external database dependencies.

## Feature Description & Value
The Clawforge framework solves the core problem of disconnected agent operations by providing a unified, self-sustaining runtime. Operators gain:
- **Zero-touch deployment**: `docker-compose up -d` starts a fully autonomous agent
- **Cryptographic security**: All signatures use CLAW_V2 domain separation; private keys never exposed
- **Self-healing reliability**: Sentinel watchdog ensures ≥99.5% uptime with automatic recovery
- **Economic sustainability**: Auto-staking at 10% with cost offset for operational self-funding
- **Audit integrity**: 100% hash-chained, tamper-evident logs for compliance and verification
- **Enterprise readiness**: RUNBOOK.md enables fresh operator deployment in <30 minutes

## Scope

**In Scope:**
- 10 modules: Protocol Loading (0), HTTPS Trust Boundary (0.1), Wallet & Auth (1), Least Privilege Credentials (1.1), Sentinel (2), Memory System (3), Fuel Credits (4), Task Discovery (5), Work Execution (6), Audit Trails (7), Dynamic Sourcing (8)
- Python 3.12+ FastAPI backend with async architecture
- File-based storage with atomic writes and file locking
- EIP-191 CLAW_V2 signing with AES-256-GCM key encryption at rest
- 3-tier memory (HOT/WARM/COLD) with auto-promotion/demotion
- Sentinel watchdog with heartbeat, Dead Man's Switch, and process restart
- USDC-pegged ledger with append-only guarantees and 10% auto-stake
- Docker Compose deployment (Tier 1 local, Tier 2 cloud)
- RUNBOOK.md, README.md, docker-compose.yml deliverables
- Security audit covering OWASP Top 10, EIP-191, cryptographic primitives

**Out of Scope:**
- Web UI or dashboard (CLI + REST API only)
- Cloud key management (AWS KMS, HashiCorp Vault) — local env vars only
- Multi-tenant isolation (single operator model)
- Cross-chain token bridging (USDC-only internal ledger)
- Machine learning model training (rule-based + heuristic logic only)
- External database dependencies (all storage file-based)

## Acceptance Criteria
1. **Functional Completeness**: All 10 modules implemented with acceptance criteria from PRD section 6 passing, including protocol loading, wallet signing, sentinel monitoring, memory management, credit economy, task lifecycle, proof generation, audit logging, and dynamic sourcing.
2. **Security & Compliance**: EIP-191 CLAW_V2 signatures verify against known test vectors; private keys never exposed to network or disk; HTTPS Trust Boundary blocks all non-`aiagentstore.ai` URLs; server signer enforces spend limits with human approval for overflows; hash chain integrity verifiable from genesis.
3. **Reliability & Self-Healing**: Sentinel heartbeat runs every 60s with ≤90s freshness; process restarts within 60s of failure detection; Dead Man's Switch triggers after 5min of silence; agent achieves ≥99.5% uptime in 24-hour test.
4. **Deployment & Operations**: `docker-compose up -d` starts complete system; RUNBOOK.md enables fresh operator deployment in <30 minutes; all Python code passes ruff lint and mypy --strict type check; README.md articulates value proposition for all stakeholder personas.
5. **Economic Correctness**: Ledger is append-only with no in-place edits; auto-stake deducts exactly 10% of every earning; reputation tiers update correctly based on cumulative earnings; settlement statements signed and verifiable.