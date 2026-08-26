# Project Guidelines: Dutchkem Ventures Clawforge

## Tech Stack (Enforced)

| Layer | Technology | Version |
|-------|-----------|---------|
| Runtime | Python | 3.12+ |
| Async | asyncio | stdlib |
| Web Framework | FastAPI | latest |
| ASGI Server | uvicorn | latest |
| Crypto (EIP-191) | eth_account | latest |
| Crypto (Keccak-256) | web3.py | latest |
| Crypto (AES-256-GCM) | cryptography | latest |
| Scheduling | APScheduler | 3.x |
| HTTP Client | httpx | latest |
| Linting | ruff | latest |
| Type Checking | mypy | latest |
| Containerization | Docker + Docker Compose | latest |

## Architectural Rules

1. **File-Based Storage Only** — No external databases (PostgreSQL, Redis, SQLite). All state lives in tiered file directories under `data/`.
2. **Append-Only Audit Logs** — Every log entry is hash-chained to the previous. Never edit or mutate existing log entries.
3. **Zero Network Key Exposure** — `CLAW_EARN_PRIVATE_KEY` is read from env, decrypted in memory only via Secret Vault, never written to disk or transmitted.
4. **HTTPS Trust Boundary** — All external HTTP requests MUST target `https://aiagentstore.ai/` only. Unknown hosts trigger pause + human approval.
5. **Least Privilege Signing** — Server signer wallet has hard spend limits. Main key is encrypted at rest (AES-256-GCM). Overflow routes to human approval queue.
6. **Domain Separation** — All signatures use EIP-191 with `CLAW_V2` prefix. No shared signing contexts.
7. **Self-Healing** — Sentinel monitors all processes via heartbeat. Failures trigger automatic restart within 60s.
8. **No Web UI** — CLI + REST API only. No frontend frameworks.
9. **Single-Tenant** — No multi-tenancy or user isolation. One operator, one agent runtime.
10. **Type Safety** — All Python code must pass `mypy --strict` and `ruff check`.

## Code Style

- Use `ruff` for linting and formatting (line length: 100)
- Type hints required on all public functions
- Use `pathlib.Path` for all file operations (no `os.path`)
- Use `httpx.AsyncClient` for HTTP (not `requests`)
- Use `structlog` for structured logging
- Use dataclasses or Pydantic models for all data structures
- Prefer `async/await` over callback-based async

## Project Structure (Recommended)

```
clawforge/
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── RUNBOOK.md
├── README.md
├── GUIDELINES.md
├── src/
│   └── clawforge/
│       ├── __init__.py
│       ├── main.py              # FastAPI app entrypoint
│       ├── config.py             # Settings & env vars
│       ├── crypto/
│       │   ├── signing.py        # EIP-191 CLAW_V2 signing
│       │   ├── hashing.py        # SHA-256 / Keccak-256
│       │   └── vault.py          # Secret Vault (AES-256-GCM encryption)
│       ├── sentinel/
│       │   ├── heartbeat.py      # Heartbeat emitter & freshness check
│       │   └── watchdog.py       # Process supervisor + Dead Man's Switch
│       ├── memory/
│       │   ├── tier.py           # HOT / WARM / COLD tier logic
│       │   ├── promotion.py      # Auto-promote/demote rules
│       │   └── prune.py          # 30-day prune cycle
│       ├── economy/
│       │   ├── ledger.py         # Append-only USDC ledger
│       │   ├── staking.py        # Auto-stake 10%
│       │   └── reputation.py     # Bronze → Diamond tiers
│       ├── tasks/
│       │   ├── discovery.py      # /claw/tasks API client
│       │   ├── bidder.py         # Smart bid logic
│       │   ├── executor.py       # Work execution + proof gen
│       │   └── sourcing.py       # Supply/demand scanner + study tasks
│       ├── audit/
│       │   ├── logger.py         # Append-only log writer
│       │   ├── chain.py          # Hash chain verification
│       │   └── settlement.py     # Settlement statement generation
│       ├── protocol/
│       │   ├── loader.py         # Fetch claw-earn.json
│       │   └── trust.py          # HTTPS Trust Boundary enforcement
│       └── credentials/
│           ├── server_signer.py  # Restricted signer with spend limits
│           └── approval.py       # Human approval queue
├── tests/
│   └── ...
└── .devhive/
    └── specs/
        ├── 00-prd.md
        └── 01-exploration.md
```

## OpenCode Skills

Global skills to enable for this project:
- `backend-architect` — Backend API and architecture patterns
- `backend-security-coder` — Security implementation (EIP-191, crypto, trust boundaries)
- `docker-expert` — Dockerfile optimization and Compose orchestration
- `devhive-*` skills — SDD pipeline orchestration
