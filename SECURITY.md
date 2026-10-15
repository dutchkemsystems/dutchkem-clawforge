# Security Policy

## Threat Model

Clawforge handles wallet signing, USDC settlement, and hash-chained audit logs.
The following threats are in scope:

### Assets under protection
- **Wallet private key** (`CLAW_EARN_PRIVATE_KEY`) — used to sign on-chain transactions
- **Vault master key** (`CLAW_VAULT_KEY`) — AES-256-GCM key encrypting the wallet private key at rest
- **Audit chain integrity** — hash-linked records that must not be silently modified
- **RPC and API credentials** — used to reach upstream services (aiagentstore.ai, RPC providers)

### Trust boundaries
- **Inbound HTTP**: FastAPI endpoints. All input is validated at the boundary with
  Pydantic models and regex patterns (`_TASK_ID_PATTERN`, `_ADDRESS_PATTERN` in `api/routes.py`).
- **Outbound HTTP**: aiagentstore.ai and configured RPC providers. All requests assume HTTPS
  termination at the edge. Plaintext HTTP is not supported in production.
- **Filesystem**: the vault file is encrypted at rest. Filesystem-level compromise of the
  host is out of scope — the master key would also need to be obtained.

### Attacker capabilities considered
- Network attacker on the public internet (mitigated by HTTPS-only outbound)
- Malicious API caller (mitigated by Pydantic validation + auth layer)
- Compromised dependency (mitigated by `pip-audit` in CI)
- Compromised CI runner (mitigated by no long-lived secrets in workflow files)

### Out of scope
- Compromise of the host OS by an attacker with root
- Compromise of the environment variable store (see "Known Gaps")

## Known Gaps and Recommended Production Practice

The current implementation stores `CLAW_EARN_PRIVATE_KEY` and `CLAW_VAULT_KEY`
as plain environment variables. This is acceptable for development and staging
but **not recommended for production**.

**Recommended production posture:**
1. Store the vault master key in a dedicated secret manager (AWS Secrets Manager,
   GCP Secret Manager, HashiCorp Vault, or Doppler).
2. Rotate the vault master key on a documented schedule.
3. Use short-lived RPC credentials where the provider supports it.
4. Run the signer in a dedicated process with least-privilege filesystem access.

## Reporting a Vulnerability

Please email **security@dutchkem.example** with:
1. A clear description of the issue
2. Steps to reproduce
3. Potential impact
4. Any suggested mitigation

**Do not open a public GitHub issue for security reports.**

We aim to acknowledge within 72 hours and provide a remediation timeline
within 7 days.

## Supported Versions

Only the latest release on `master` is supported with security updates.

## Disclosure

We follow coordinated disclosure. Once a fix ships, we publish an advisory
crediting the reporter (unless anonymity is requested).
