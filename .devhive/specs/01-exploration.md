# Phase 01: Exploration

## Executive Summary

The Clawforge framework is a greenfield Python 3.12+ project that builds an autonomous AI agent runtime for the Claw Earn marketplace. It combines cryptographic authentication (EIP-191 CLAW_V2), self-healing supervision (Sentinel), a tiered file-based memory system, and an internal USDC-pegged economy — all within a single Docker-deployable unit with zero external database dependencies. The codebase will be approximately 8–12 modules across ~50 source files.

## Tech Stack & Guidelines

Per `GUIDELINES.md` (created):

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.12+, asyncio |
| Web Framework | FastAPI + uvicorn |
| Crypto | eth_account (EIP-191), web3.py (Keccak-256), cryptography (AES-256-GCM) |
| Scheduling | APScheduler 3.x |
| HTTP | httpx (async) |
| Storage | File-based (no external DB) |
| Logging | structlog |
| Linting/Types | ruff, mypy --strict |
| Deployment | Docker + Docker Compose |

**Key architectural rules:** File-based storage only, append-only hash-chained audit logs, zero network key exposure, HTTPS Trust Boundary (aiagentstore.ai only), least-privilege signing with spend limits, EIP-191 CLAW_V2 domain separation, self-healing Sentinel, CLI + REST API only, single-tenant.

## User Needs

**Core problem:** AI agents cannot autonomously participate in the Claw Earn marketplace without a unified runtime that handles wallet security, self-healing, economic self-funding, and audit-grade reporting. Operators currently manage agent lifecycles manually — authentication, task discovery, bidding, proof submission, and settlement are all disconnected processes.

**What this feature solves:** End-to-end autonomous agent operation with zero manual intervention after `docker-compose up`. The agent discovers tasks, bids, executes work, generates cryptographic proofs, settles credits, and self-heals from failures — all while maintaining tamper-evident audit trails and staying within cryptographic spending limits.

## Affected Areas

| Area | Files (Planned) | Reason |
|------|-----------------|--------|
| **Crypto Layer** | `src/clawforge/crypto/signing.py`, `hashing.py`, `vault.py` | EIP-191 CLAW_V2 domain-separated signing, Keccak-256 proof hashing, AES-256-GCM key encryption at rest |
| **Sentinel** | `src/clawforge/sentinel/heartbeat.py`, `watchdog.py` | APScheduler-driven 60s heartbeat, 90s freshness check, Dead Man's Switch (5min), process restart logic |
| **Memory System** | `src/clawforge/memory/tier.py`, `promotion.py`, `prune.py` | HOT/WARM/COLD file-based tiers, auto-promote (>5 accesses/hr), auto-demote (30min idle), 30-day prune |
| **Economy** | `src/clawforge/economy/ledger.py`, `staking.py`, `reputation.py` | Append-only USDC ledger, 10% auto-stake, cost offset, reputation tiers |
| **Task Lifecycle** | `src/clawforge/tasks/discovery.py`, `bidder.py`, `executor.py`, `sourcing.py` | /claw/tasks API client, smart bidding, proof generation, supply/demand scanner, study tasks |
| **Audit** | `src/clawforge/audit/logger.py`, `chain.py`, `settlement.py` | Hash-chained append-only logs, chain verification, signed settlement statements |
| **Protocol** | `src/clawforge/protocol/loader.py`, `trust.py` | Remote spec fetching, HTTPS Trust Boundary enforcement |
| **Credentials** | `src/clawforge/credentials/server_signer.py`, `approval.py` | Restricted signer with spend limits, human approval queue |
| **Config** | `src/clawforge/config.py` | Environment variable loading (wallet, key, URLs, limits) |
| **API** | `src/clawforge/main.py` | FastAPI app, health endpoints, REST interface |
| **Deployment** | `Dockerfile`, `docker-compose.yml` | Multi-stage build, Tier 1/2 deployment configs |

## Dependencies & Constraints

### External Dependencies (PyPI)
| Package | Purpose | Risk |
|---------|---------|------|
| `eth_account` | EIP-191 message signing | Core auth — must pin version, test against known vectors |
| `web3.py` | Keccak-256 hashing | Heavy dependency; consider `pysha3` or `pycryptodome` as lighter alternative if only hashing is needed |
| `cryptography` | AES-256-GCM for key encryption | Mature, well-audited; pin to >=41.x for stable API |
| `APScheduler` | Heartbeat scheduling, cron jobs | v3.x is stable; ensure async-compatible executor |
| `httpx` | Async HTTP client for marketplace API | Required for trust boundary enforcement (response tracking) |
| `fastapi` + `uvicorn` | REST API framework | Well-established; pin versions |
| `structlog` | Structured logging | Lightweight, async-friendly |
| `pydantic` | Data validation (via FastAPI) | Required for API contract models |
| `ruff` | Linting | Dev dependency only |
| `mypy` | Type checking | Dev dependency only |

### Technical Constraints

1. **No external database** — All state (memory tiers, ledger, audit logs, task state) must be stored as files on disk. Requires careful design of file locking, atomic writes, and corruption recovery.
2. **EIP-191 domain separation** — Signing format must be exactly `\x19Ethereum Signed Message:\n{len(message)}{message}` prefixed with `CLAW_V2`. Any deviation breaks marketplace verification.
3. **APScheduler async integration** — Heartbeat jobs must run in the asyncio event loop. Requires `AsyncIOScheduler` with proper job misfire handling.
4. **Hash chain integrity** — Each audit log entry hashes the previous entry's hash. Chain must be verifiable from genesis. Corruption of any single entry invalidates all subsequent entries.
5. **File locking for concurrency** — Concurrent access to shared files (ledger, task state) requires OS-level file locks (`fcntl` on Linux, `msvcrt` on Windows). The Docker deployment is Linux-only, so `fcntl` is sufficient.
6. **Secret Vault encryption** — Main private key is AES-256-GCM encrypted at rest. Decryption requires a vault key (also env var). Both keys must never coexist in the same process memory longer than needed for the signing operation.
7. **Trust boundary enforcement** — Every external HTTP call must validate the target URL against `https://aiagentstore.ai/`. Redirects to non-Claw hosts must be caught and blocked. Requires intercepting httpx redirect flow.
8. **Docker multi-stage build** — Final image must be minimal (python:3.12-slim). Build stage installs dev deps; runtime stage copies only production artifacts.
9. **Append-only ledger** — The USDC ledger file is append-only. No in-place edits. Pruning is done by archival, not deletion.
10. **90-day log retention** — Audit logs must be retained for 90 days minimum. Pruning policy must archive before deletion.

### Platform Constraints
- **Target OS:** Linux (Docker deployment). File locking uses `fcntl`.
- **Python version:** 3.12+ required (match/case, type parameter syntax, improved asyncio).
- **No cloud services:** No AWS KMS, no HashiCorp Vault, no managed databases.

## Complexity

**High**

Justification:
- 8+ modules with interdependencies (crypto → signing, Sentinel → heartbeat → memory, economy → ledger → staking → reputation)
- Cryptographic correctness is critical (EIP-191, AES-256-GCM, hash chaining)
- File-based storage under concurrency requires careful atomic write and locking design
- Self-healing supervision with Dead Man's Switch adds state machine complexity
- Economic ledger with append-only guarantees and auto-staking requires transactional correctness
- Trust boundary enforcement must handle HTTP redirect interception
- Multiple failure modes to handle gracefully (network, disk, crypto, process)

## Risks

| # | Risk | Severity | Impact | Mitigation |
|---|------|----------|--------|------------|
| 1 | **Private key exposure** | Critical | Catastrophic — wallet compromise, fund theft | Keys never leave env vars; decrypted in memory only for exact signing op; AES-256-GCM at rest; no disk write; no network transmission |
| 2 | **EIP-191 signing deviation** | Critical | Marketplace rejects all signatures; agent cannot authenticate | Implement against known test vectors; unit test with official Claw verification; pin eth_account version |
| 3 | **Hash chain corruption** | High | Audit trail invalid; compliance failure | Integrity checks on every write; periodic full-chain verification; backup before prune |
| 4 | **File locking race conditions** | High | Ledger double-spend, memory corruption | Use `fcntl.flock()` with proper error handling; atomic write via temp file + rename |
| 5 | **APScheduler job misfire** | High | Heartbeat missed; false Dead Man's Switch trigger | Configure `misfire_grace_time`; use `Coalesce missed=True`; monitor job execution times |
| 6 | **Marketplace API downtime** | Medium | Agent cannot discover tasks; earnings stall | Graceful degradation; cached task specs; retry with exponential backoff; fallback to study tasks |
| 7 | **Docker image bloat** | Medium | Slow deployment; larger attack surface | Multi-stage build; pin base image; exclude dev deps from runtime stage |
| 8 | **AES-256-GCM vault key management** | High | If vault key is weak or leaked, all encrypted keys are compromised | Enforce minimum key entropy; vault key from separate env var; key rotation support |
| 9 | **Trust boundary redirect bypass** | Critical | Agent connects to malicious host; data/key exfiltration | Intercept httpx redirect chain; validate each hop against allowlist; block on any non-Claw host |
| 10 | **Memory tier promotion/demotion storms** | Medium | Excessive file I/O; data thrashing between tiers | Debounce promotion checks; minimum dwell time before demotion; rate-limit tier transitions |
| 11 | **Append-only ledger growth** | Medium | Disk space exhaustion over time | Archive old entries to compressed files; 90-day retention policy with archival |
| 12 | **Windows development vs Linux deployment** | Low | File locking API differences (`msvcrt` vs `fcntl`) | Use conditional imports; test on Linux in CI; document Linux-only deployment requirement |
