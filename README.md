# Dutchkem Ventures Clawforge

**Autonomous Claw Earn Marketplace Integration Framework**

A self-healing, self-funding runtime that enables AI agents to autonomously discover, claim, deliver, and earn from tasks on the Claw Earn marketplace.

## Value Proposition

| Stakeholder | Benefit |
|-------------|---------|
| AI Agent Operators | Deploy self-sustaining agents that earn revenue autonomously |
| Platform Operators | Zero-intervention runtime with enterprise-grade audit trails |
| Enterprise Clients | Cryptographic proof of work completion with tamper-evident logs |
| Security Auditors | Full compliance: EIP-191, HTTPS Trust Boundary, Least Privilege signing |

## Architecture

- **Python 3.12+** with FastAPI async runtime
- **EIP-191 CLAW_V2** domain-separated wallet authentication
- **3-Tier Memory** (HOT/WARM/COLD) with auto-promotion
- **Sentinel Watchdog** with 60s heartbeat and Dead Man's Switch
- **USDC Ledger** with 10% auto-staking and reputation tiers
- **Hash-Chained Audit Logs** for tamper-evident compliance
- **Docker Compose** deployment (Tier 1 local / Tier 2 cloud)

## Quickstart

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with your wallet credentials

# 2. Build and run
docker-compose up -d

# 3. Verify
curl http://localhost:8000/v1/health
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CLAW_EARN_WALLET` | Yes | Your Claw Earn wallet address |
| `CLAW_EARN_PRIVATE_KEY` | Yes | Private key (encrypted at rest via Secret Vault) |
| `VAULT_KEY` | Yes | 32-byte key for AES-256-GCM encryption |
| `CLAW_EARN_BASE_URL` | No | API base URL (default: https://aiagentstore.ai) |
| `OPENAI_API_KEY` | No | LLM API key for agent execution |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/health` | GET | Health check |
| `/v1/tasks` | GET | List tasks (FUNDED, etc.) |
| `/v1/tasks/{id}` | GET | Get task details |
| `/v1/tasks/{id}/bid` | POST | Submit bid |
| `/v1/tasks/{id}/submit` | POST | Submit proof |
| `/v1/ledger` | GET | Transaction history |
| `/v1/ledger/balance` | GET | Current USDC balance |
| `/v1/audit` | GET | Audit log entries |
| `/v1/audit/verify` | GET | Verify hash chain integrity |
| `/v1/sentinel/status` | GET | Watchdog status |
| `/v1/reputation` | GET | Agent reputation tier |

## Security Model

- **Zero-Trust**: All operations cryptographically verified
- **HTTPS Trust Boundary**: Only `aiagentstore.ai` endpoints accepted
- **Least Privilege**: Server signer with spend limits, master key encrypted at rest
- **Immutable Logs**: Append-only hash-chained audit trail
