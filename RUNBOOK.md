# RUNBOOK.md — Clawforge Operations Manual

> **Target audience:** AI Agent Operators deploying and maintaining a Clawforge instance.
> **Goal:** Fresh operator deployment in under 30 minutes.

---

## 1. Prerequisites

### 1.1 Server Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 cores | 4 cores |
| RAM | 4 GB | 8 GB |
| Disk | 20 GB | 50 GB (grows with audit logs) |
| OS | Linux (Ubuntu 22.04+, Debian 12+) | Ubuntu 24.04 LTS |
| Network | Outbound HTTPS to `aiagentstore.ai` | Low-latency to marketplace |

### 1.2 Software Requirements

| Dependency | Version |
|------------|---------|
| Python | 3.12+ |
| Docker | 24.0+ |
| Docker Compose | v2.20+ |

### 1.3 Environment Variables

Set the following in your `.env` file (copy from `.env.example`):

| Variable | Description | Example |
|----------|-------------|---------|
| `CLAW_EARN_WALLET` | Agent wallet address (0x-prefixed, EIP-55 checksum) | `0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B` |
| `CLAW_EARN_PRIVATE_KEY` | Encrypted private key (AES-256-GCM via Secret Vault) | `vault:v1:...` |
| `VAULT_KEY` | 32-byte vault decryption key (used to decrypt `CLAW_EARN_PRIVATE_KEY` in memory) | `your-32-byte-key-here` |
| `OPENAI_API_KEY` | API key for OpenAI-powered task analysis | `sk-...` |
| `MEMORY_PATH` | Absolute path to persistent memory directory | `/data/memory` |
| `CLAW_API_BASE_URL` | Marketplace API endpoint (default: `https://aiagentstore.ai`) | `https://aiagentstore.ai` |

### 1.4 Crypto Requirements

| Asset | Purpose | Min Balance |
|-------|---------|-------------|
| ETH | Gas fees for on-chain proof submission (Keccak-256 tasks) | 0.01 ETH |
| USDC | Staking capital (10% auto-staked per earning) | 50 USDC recommended |

---

## 2. Deployment Steps

### 2.1 Clone the Repository

```bash
git clone https://github.com/dutchkem-ventures/clawforge.git
cd clawforge
```

### 2.2 Configure Environment

```bash
cp .env.example .env
# Edit .env with your values
nano .env
```

**Verify critical variables are set:**

```bash
grep -E "CLAW_EARN_WALLET|CLAW_EARN_PRIVATE_KEY|VAULT_KEY" .env
```

### 2.3 Build the Docker Image

```bash
docker compose build
```

This runs the multi-stage build (builder + runtime) using `python:3.12-slim`.

### 2.4 Start the Service

```bash
docker compose up -d
```

**For cloud deployment (Tier 2):**

```bash
docker compose -f docker-compose.yml --profile cloud up -d
```

### 2.5 Verify Health Endpoint

```bash
curl http://localhost:8000/v1/health
```

Expected response:

```json
{
  "status": "healthy",
  "uptime": 12345
}
```

If the health check fails, check container logs:

```bash
docker compose logs -f clawforge
```

---

## 3. Initial Setup & First Run

After deploying, verify the following before the agent begins task scanning.

### 3.1 Verify Connection to aiagentstore.ai

```bash
curl -s http://localhost:8000/v1/status | jq '.marketplace_connection'
```

Expected: `"connected"` or equivalent healthy state. If unreachable, check:
- Network egress to `https://aiagentstore.ai`
- DNS resolution: `nslookup aiagentstore.ai`
- Firewall rules (outbound HTTPS on port 443)

### 3.2 Confirm Memory Directories Created

```bash
ls -la /data/memory/
# Expected: hot/  warm/  cold/
ls -la /data/economy/
# Expected: ledger.jsonl  staking.json  reputation.json
ls -la /data/audit/
# Expected: chain.jsonl  settlements/  backups/
```

If directories are missing, check the `MEMORY_PATH` env var and volume mount permissions.

### 3.3 Check Ledger for Staking Reserves

```bash
curl -s http://localhost:8000/v1/economy/balance | jq '.'
curl -s http://localhost:8000/v1/economy/staking | jq '.'
```

Verify that the `staking.json` shows the initial 10% auto-stake position. The ledger (`ledger.jsonl`) should be empty or contain only the initial credit entry.

### 3.4 Validate Wallet Signature with Test Message

The Sentinel performs this automatically on startup. Check logs for:

```
Wallet signature verified successfully
```

If verification fails, the agent will refuse to start. Verify:
- `CLAW_EARN_WALLET` matches the address derived from the private key
- `VAULT_KEY` correctly decrypts the encrypted private key
- The wallet has not been rotated without updating the env var

---

## 4. Monitoring & Observability

### 4.1 Heartbeats

The Sentinel emits a heartbeat every 60 seconds. Check status:

```bash
curl -s http://localhost:8000/v1/sentinel/status | jq '.'
```

| Field | Healthy Value | Warning |
|-------|---------------|---------|
| `status` | `"healthy"` | `"degraded"` or `"failed"` |
| `heartbeat_age_seconds` | `< 90` | `>= 90` |
| `restart_count` | `0` | `> 0` |

**Heartbeat stale (>90s):** Warning logged automatically.
**Dead Man's Switch (5min silence):** Critical alert triggers operator notification + graceful shutdown.

### 4.2 Task Discovery Logs

Monitor task scanning and bidding:

```bash
docker compose logs -f clawforge 2>&1 | grep -i "task\|bid"
```

Key log events:
- `task_discovered` — New funded task found
- `bid_submitted` — Smart bidder placed a bid
- `bid_accepted` — Agent accepted for task
- `work_dispatched` — Specialized agent started execution
- `proof_submitted` — Proof sent to marketplace

### 4.3 Financial Health

```bash
curl -s http://localhost:8000/v1/economy/balance | jq '.'
curl -s http://localhost:8000/v1/economy/reputation | jq '.'
curl -s http://localhost:8000/v1/economy/ledger?limit=20 | jq '.'
```

| Metric | Healthy Range | Action Required |
|--------|---------------|-----------------|
| USDC balance | > 10 USDC | Fund wallet if low |
| Daily stake | < limit | Check `spend_limits.json` |
| Reputation tier | bronze+ | Review task success rate |

### 4.4 Reputation Tiers

```bash
curl -s http://localhost:8000/v1/economy/reputation | jq '.tier'
```

| Tier | Min Earnings | Auto-Start Threshold |
|------|-------------|---------------------|
| Bronze | 0 USDC | < $100 |
| Silver | 500 USDC | < $250 |
| Gold | 2,000 USDC | < $500 |
| Platinum | 10,000 USDC | < $1,000 |
| Diamond | 50,000 USDC | < $5,000 |

### 4.5 Audit Chain Verification

```bash
curl -s -X POST http://localhost:8000/v1/audit/verify | jq '.'
```

Expected response:

```json
{
  "valid": true,
  "entries_verified": 1234,
  "chain_start": "0x...",
  "chain_end": "0x...",
  "verified_at": "2026-08-26T12:00:00Z"
}
```

If `valid: false`, the hash chain has been tampered with or corrupted. See Section 5.4.

---

## 5. Emergency Failover

### 5.1 Agent Crash Handling

**Automatic recovery:** The Sentinel restarts the agent within 60 seconds of detecting failure.

**Manual restart:**

```bash
curl -s -X POST http://localhost:8000/v1/sentinel/restart
```

Or restart the Docker container:

```bash
docker compose restart clawforge
```

**Check restart history:**

```bash
curl -s http://localhost:8000/v1/sentinel/status | jq '.restart_count'
cat /data/sentinel/restart_count.json
```

### 5.2 Protect Staked Capital

If the agent is malfunctioning and may submit invalid proofs, immediately reclaim staked capital:

```bash
curl -s -X POST http://localhost:8000/v1/tasks/{task_id}/stake-reclaim
```

This triggers:
1. Cancellation of any in-progress bid
2. Reclamation of staked USDC from the marketplace
3. Logging of the reclaim event in the audit chain
4. Entry into safe mode (no new bids until operator review)

**Nuclear option — stop all activity:**

```bash
docker compose stop clawforge
```

### 5.3 Key Compromise Response

If `CLAW_EARN_PRIVATE_KEY` or `VAULT_KEY` is suspected compromised:

1. **Stop the agent immediately:**
   ```bash
   docker compose stop clawforge
   ```

2. **Generate a new wallet:**
   ```bash
   # Use a secure, air-gapped environment
   python3 -c "from eth_account import Account; a = Account.create(); print(f'Address: {a.address}'); print(f'Key: {a.key.hex()}')"
   ```

3. **Re-encrypt the new private key with a new VAULT_KEY:**
   ```bash
   python3 -c "
   from cryptography.fernet import Fernet
   key = Fernet.generate_key()
   print(f'New VAULT_KEY: {key.decode()}')
   "
   ```

4. **Update `.env` with new values**

5. **Redeploy:**
   ```bash
   docker compose up -d
   ```

6. **Verify new wallet on marketplace:**
   ```bash
   curl -s http://localhost:8000/v1/status | jq '.wallet'
   ```

### 5.4 Dead Man's Switch Escalation

The Dead Man's Switch triggers when the agent is silent for 5+ minutes.

**Escalation ladder:**

| Silence Duration | Action |
|-----------------|--------|
| 0–60s | Normal operation |
| 60–90s | Warning logged |
| 90–300s | Sentinel attempts restart |
| 300s+ (5min) | **Dead Man's Switch fires:** critical alert + graceful shutdown + operator notification |

**Manual override:**

```bash
# Reset the Dead Man's Switch timer
curl -s -X POST http://localhost:8000/v1/sentinel/restart

# Check DMS state
cat /data/sentinel/dead_mans_switch.json
```

---

## 6. Troubleshooting

### 6.1 Permission Denied

**Symptoms:** `PermissionError` in logs, Docker socket errors, file write failures.

**Solutions:**

```bash
# Fix data directory permissions
sudo chown -R 1000:1000 /data/

# Fix Docker socket permissions (if non-root user)
sudo usermod -aG docker $USER
# Log out and back in

# Verify volume mount permissions
docker compose exec clawforge ls -la /app/data
```

**Docker socket error (Cannot connect to Docker daemon):**

```bash
sudo systemctl start docker
sudo systemctl enable docker
```

### 6.2 No Tasks Available

**Symptoms:** Agent logs show `no_funded_tasks`, idle state persists.

**Diagnostics:**

```bash
# Check task inventory
curl -s http://localhost:8000/v1/tasks | jq '. | length'

# Check marketplace connectivity
curl -s http://localhost:8000/v1/status | jq '.marketplace_connection'
```

**Solutions:**
1. Verify internet connectivity to `https://aiagentstore.ai`
2. Check if anti-starvation (Dynamic Sourcing) is active:
   ```bash
   cat /data/memory/hot/runtime_state.json | jq '.fallback_mode'
   ```
3. If `fallback_mode: true`, the agent is generating Study Tasks from WARM memory. This is normal when marketplace inventory is low.
4. Ensure `CLAW_API_BASE_URL` is correct (not `http://` — must be `https://`)

### 6.3 Insufficient USDC

**Symptoms:** Tasks skipped with `insufficient_funds` log entry.

**Diagnostics:**

```bash
curl -s http://localhost:8000/v1/economy/balance | jq '.'
cat /data/credentials/spend_limits.json | jq '.'
```

**Solutions:**
1. Fund the agent wallet with additional USDC
2. Reduce auto-stake percentage (requires config update):
   ```bash
   curl -s -X PUT http://localhost:8000/v1/config/limits \
     -H "Content-Type: application/json" \
     -d '{"auto_stake_pct": 5}'
   ```
3. Review and adjust daily spend limits in `spend_limits.json`
4. Check for stuck bids that may have locked USDC:
   ```bash
   curl -s http://localhost:8000/v1/tasks | jq '.[] | select(.status == "bitten")'
   ```

### 6.4 Trust Boundary Violations

**Symptoms:** `TRUST_BOUNDARY_VIOLATION` critical alert, agent paused.

**Diagnostics:**

```bash
# Check audit logs for violations
curl -s "http://localhost:8000/v1/audit/logs?since=2026-08-26" | jq '.[] | select(.action == "trust_boundary_violation")'
```

**Solutions:**
1. **URL blocked (not https://aiagentstore.ai):** Verify `CLAW_API_BASE_URL` matches `https://aiagentstore.ai`
2. **Redirect detected to non-Claw host:** This is a security feature. Investigate the redirect source.
3. **Unknown auth model:** Pause and review the external request. Human approval is required to proceed.
4. **Resume after investigation:**
   ```bash
   curl -s -X POST http://localhost:8000/v1/sentinel/restart
   ```

### 6.5 Spend Limit Exceeded

**Symptoms:** `SPEND_LIMIT_EXCEEDED` critical alert, transaction blocked, entry in approval queue.

**Diagnostics:**

```bash
cat /data/credentials/approval_queue.json | jq '.'
cat /data/credentials/spend_limits.json | jq '.'
```

**Solutions:**
1. **Review the pending approval:**
   ```bash
   cat /data/credentials/approval_queue.json | jq '.[]'
   ```
2. **Approve or reject the transaction:**
   - To approve: manually edit `approval_queue.json` and set `"approved": true`
   - To reject: remove the entry from the queue
3. **Adjust spend limits** (after security review):
   ```bash
   curl -s -X PUT http://localhost:8000/v1/config/limits \
     -H "Content-Type: application/json" \
     -d '{"max_gas_per_tx": "0.005", "max_usdc_stake_per_day": "200"}'
   ```
4. **Critical:** Spend limit violations indicate potential economic manipulation. Review audit logs before adjusting limits.

---

## Appendix: Quick Reference

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/health` | GET | Health check |
| `/v1/status` | GET | Agent state overview |
| `/v1/sentinel/status` | GET | Sentinel health & restart count |
| `/v1/sentinel/restart` | POST | Manual restart trigger |
| `/v1/tasks` | GET | List discovered tasks |
| `/v1/tasks/{id}/proof` | GET | Retrieve task proof |
| `/v1/tasks/{id}/stake-reclaim` | POST | Reclaim staked capital |
| `/v1/economy/balance` | GET | Current USDC balance |
| `/v1/economy/staking` | GET | Staking position |
| `/v1/economy/reputation` | GET | Reputation tier & score |
| `/v1/economy/ledger` | GET | Recent ledger entries |
| `/v1/audit/logs` | GET | Audit logs with hash chain |
| `/v1/audit/verify` | POST | Verify hash chain integrity |
| `/v1/memory/{tier}` | GET | Memory entries by tier |
| `/v1/config` | GET | Runtime configuration |
| `/v1/config/limits` | PUT | Update spend limits |

### Log Levels

| Level | Meaning |
|-------|---------|
| `DEBUG` | Verbose diagnostic info (development only) |
| `INFO` | Normal operations (task discovery, bids, proofs) |
| `WARNING` | Recoverable issues (heartbeat stale, retry in progress) |
| `ERROR` | Failure requiring intervention (proof submission failed, API down) |
| `CRITICAL` | Security or integrity event (trust boundary, spend limit, chain corruption) |

### File Locations

| Path | Contents |
|------|----------|
| `/data/memory/hot/` | Real-time operational state |
| `/data/memory/warm/` | Lessons learned, patterns |
| `/data/memory/cold/` | Identity, reputation, history |
| `/data/economy/ledger.jsonl` | Append-only USDC ledger |
| `/data/economy/staking.json` | Current stake position |
| `/data/audit/chain.jsonl` | Hash-chained audit logs |
| `/data/credentials/spend_limits.json` | Current spend limits |
| `/data/credentials/approval_queue.json` | Pending human approvals |
| `/data/sentinel/heartbeat.json` | Latest heartbeat state |
| `/data/sentinel/dead_mans_switch.json` | DMS state |
