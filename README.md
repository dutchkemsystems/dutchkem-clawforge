# Dutchkem Ventures Clawforge

**Autonomous Claw Earn Marketplace Integration Framework**

A self-healing, self-funding runtime that enables AI agents to autonomously discover, claim, deliver, and earn from tasks on the Claw Earn marketplace. Built on Base chain with USDC settlement.

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
- **On-Chain Settlement** on Base chain with USDC transfers
- **WebSocket Events** for real-time task monitoring
- **AI Agent Execution** via OpenAI (GPT-4o-mini) with fallback
- **Docker Compose** deployment (Tier 1 local / Tier 2 cloud)

## Quickstart

```bash
# 1. Clone and configure
git clone https://github.com/dutchkemsystems/dutchkem-clawforge.git
cd dutchkem-clawforge
cp .env.example .env
# Edit .env with your wallet credentials

# 2. Install dependencies
pip install -e .

# 3. Run
uvicorn clawforge.main:app --host 0.0.0.0 --port 8000

# 4. Verify
curl http://localhost:8000/v1/health
```

### Docker

```bash
docker-compose up -d
# Or build manually:
docker build -t clawforge .
docker run -p 8000:8000 --env-file .env clawforge
```

### Cloud Deploy

**Render:**
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

**Fly.io:**
```bash
fly auth login
fly launch
fly secrets set CLAW_EARN_WALLET=0x... CLAW_EARN_PRIVATE_KEY=0x...
fly deploy
```

**Railway:**
```bash
railway login
railway init
railway up
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CLAW_EARN_WALLET` | Yes | Your Claw Earn wallet address (0x...) |
| `CLAW_EARN_PRIVATE_KEY` | Yes | Private key for signing (encrypted at rest) |
| `VAULT_KEY` | Yes | 32-byte key for AES-256-GCM vault encryption |
| `CLAW_EARN_BASE_URL` | No | API base URL (default: https://aiagentstore.ai) |
| `OPENAI_API_KEY` | No | LLM API key for AI agent execution |
| `API_KEY` | No | API authentication key (empty = disabled for dev) |
| `SENTINEL_HEARTBEAT_INTERVAL` | No | Heartbeat interval in seconds (default: 60) |
| `SENTINEL_FRESHNESS_THRESHOLD` | No | Stale threshold in seconds (default: 90) |
| `SENTINEL_DEAD_MAN_SWITCH` | No | Dead man's switch in seconds (default: 300) |
| `AUTO_STAKE_PERCENTAGE` | No | Auto-stake percentage (default: 0.10) |
| `MAX_DAILY_STAKE_USDC` | No | Max daily stake in USDC (default: 1000.0) |

## API Reference

Interactive docs available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Health Check

```bash
curl http://localhost:8000/v1/health
```

```json
{
  "status": "ok",
  "service": "clawforge",
  "timestamp": 1787761573.168
}
```

### Task Management

```bash
# List funded tasks
curl http://localhost:8000/v1/tasks?status=FUNDED

# Get task details
curl http://localhost:8000/v1/tasks/task-123

# Submit a bid (10% auto-staked)
curl -X POST "http://localhost:8000/v1/tasks/task-123/bid?bid_amount=50.0"

# Submit proof of work
curl -X POST http://localhost:8000/v1/tasks/task-123/submit

# Reclaim stake after completion
curl -X POST http://localhost:8000/v1/tasks/task-123/stake-reclaim
```

### Full Lifecycle (Bid + Execute + Settle)

```bash
curl -X POST "http://localhost:8000/v1/tasks/task-123/full-lifecycle?bid_amount=50.0&to_address=0xRecipientAddress"
```

```json
{
  "task_id": "task-123",
  "bid": {"amount": 50.0, "stake": 5.0},
  "execution": {"success": true, "output": "...", "agent_type": "general"},
  "settlement": {"status": "queued", "to_address": "0x...", "amount_usdc": 50.0},
  "ledger": {"reclaimed": 5.0}
}
```

### On-Chain Settlement

```bash
# Submit settlement to Base chain
curl -X POST "http://localhost:8000/v1/settlement/task-123/submit?to_address=0x...&amount_usdc=50.0"

# Check settlement status
curl http://localhost:8000/v1/settlement/task-123/status
```

### Economy

```bash
# Get USDC balance
curl http://localhost:8000/v1/ledger/balance

# Get transaction history
curl http://localhost:8000/v1/ledger

# Get reputation tier
curl http://localhost:8000/v1/reputation

# Rate a task (0-5)
curl -X POST "http://localhost:8000/v1/reputation/rate?task_id=task-123&rating=4.5"
```

### Monitoring

```bash
# Sentinel watchdog status
curl http://localhost:8000/v1/sentinel/status

# Audit chain verification
curl http://localhost:8000/v1/audit/verify

# Trust boundary approvals
curl http://localhost:8000/v1/trust/pending-approvals
```

### WebSocket Events

```javascript
// Connect to real-time events
const ws = new WebSocket("ws://localhost:8000/ws/events");

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`${data.type}: ${data.task_id}`, data.data);
};

// Filter by topic
const ws2 = new WebSocket("ws://localhost:8000/ws/events?topic=settlement");
```

Event types:
- `task_bid` — Bid submitted
- `task_executed` — Task completed
- `task_completed` — Task finished
- `settlement_submitted` — Settlement queued

## Project Structure

```
clawforge/
├── src/clawforge/
│   ├── main.py              # FastAPI app with lifespan
│   ├── config.py            # Pydantic settings
│   ├── models.py            # All Pydantic models
│   ├── api/
│   │   ├── routes.py        # 20+ REST endpoints
│   │   ├── auth.py          # API key middleware
│   │   └── ratelimit.py     # Rate limiting
│   ├── auth/
│   │   ├── wallet.py        # Wallet management
│   │   └── credentials.py   # Server signer
│   ├── crypto/
│   │   ├── signer.py        # EIP-191 CLAW_V2 signing
│   │   ├── vault.py         # AES-256-GCM encryption
│   │   └── hasher.py        # SHA-256 / Keccak-256
│   ├── economy/
│   │   ├── ledger.py        # USDC ledger with hash chain
│   │   ├── staker.py        # Auto-staker (10%)
│   │   └── reputation.py    # Tier system (bronze→diamond)
│   ├── execution/
│   │   ├── executor.py      # AI agent dispatch (OpenAI)
│   │   ├── proof.py         # SHA-256 / Keccak-256 proofs
│   │   └── a2a.py           # Agent-to-agent queue
│   ├── memory/
│   │   ├── hot.py           # In-memory hot cache
│   │   ├── warm.py          # File-backed warm storage
│   │   └── cold.py          # Cold archive
│   ├── sentinel/
│   │   └── watcher.py       # Heartbeat + Dead Man's Switch
│   ├── protocol/
│   │   ├── trust.py         # HTTPS trust boundary
│   │   └── loader.py        # Protocol spec loader
│   ├── settlement/
│   │   └── onchain.py       # Base chain USDC settlement
│   ├── events/
│   │   └── bus.py           # WebSocket event bus
│   └── tasks/
│       ├── discovery.py     # Task discovery
│       ├── bidder.py        # Smart bidding
│       └── sourcer.py       # Supply/demand scanner
├── tests/                   # 260+ tests
├── Dockerfile
├── docker-compose.yml
├── render.yaml              # Render deploy
├── fly.toml                 # Fly.io deploy
├── railway.json             # Railway deploy
└── pyproject.toml
```

## Security

- **Zero-Trust**: All operations cryptographically verified
- **HTTPS Trust Boundary**: Only `aiagentstore.ai` endpoints accepted
- **Least Privilege**: Server signer with spend limits, master key encrypted at rest
- **Immutable Logs**: Append-only hash-chained audit trail
- **Rate Limiting**: 100 requests/minute per IP
- **API Key Auth**: Optional X-API-Key header authentication

## License

MIT
