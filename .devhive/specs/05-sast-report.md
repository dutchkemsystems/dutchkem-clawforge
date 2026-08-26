# Phase 05: SAST Report

## Executive Summary

The Clawforge codebase demonstrates solid cryptographic fundamentals (AES-256-GCM, EIP-191 signing, SHA-256 hashing) and uses environment-based secret management. However, the application has **no API authentication or rate limiting**, leaving all endpoints publicly exposed. Several input validation gaps and a TOCTOU race condition in the ledger pose medium-term risks. The trust boundary hostname matching is too permissive, allowing subdomain spoofing.

## Vulnerabilities Found

| Severity | Vulnerability Type | Affected File:Line | Status/Recommendation |
|----------|-------------------|--------------------|-----------------------|
| **Critical** | No API Authentication | `api/routes.py:1-53` | All endpoints (bid, submit, ledger, audit, settlement) are publicly accessible. Add API key or JWT auth middleware. |
| **Critical** | No Rate Limiting | `api/routes.py:1-53` | Zero rate limiting on any endpoint. Add `slowapi` or FastAPI rate limiter to prevent DoS/abuse. |
| **High** | Path Traversal | `crypto/hasher.py:128-141` | `hash_file_content(file_path)` accepts arbitrary paths with no validation. Add path canonicalization and allowlist check. |
| **High** | Unvalidated API Inputs | `api/routes.py:12,20,36` | `task_id`, `bid_amount`, `status`, `since` params have no format/range validation. Use Pydantic models or `Query(..., pattern=...)`. |
| **High** | TOCTOU Race Condition | `economy/ledger.py:48-54` | Read-then-write on ledger file allows data loss under concurrency. Use file locking (`fcntl.flock` or `filelock` library). |
| **Medium** | Subdomain Spoofing in Trust Boundary | `protocol/trust.py:56` | `hostname.endswith(ALLOWED_HOST)` matches `evil-aiagentstore.ai`. Use `hostname == ALLOWED_HOST or hostname.endswith(f".{ALLOWED_HOST}")`. |
| **Medium** | No CORS Configuration | `main.py:28-33` | FastAPI app has no CORS middleware. Add explicit `CORSMiddleware` with restricted origins. |
| **Medium** | Ineffective Memory Zeroization | `crypto/vault.py:100-102` | `decrypted = "0" * len(decrypted)` fails because Python strings are immutable. Use `bytearray` + explicit overwrite, or `ctypes.memset`. |
| **Medium** | Dead Code / Bug | `auth/credentials.py:73` | `limit_path.with_suffix(".tmp") if False else ...` - `if False` is dead code suggesting a leftover bug. Remove the ternary. |
| **Medium** | Exception Info Leakage | `crypto/vault.py:81` | `VaultError(f"Decryption failed: {e}")` may expose internal crypto error details to callers. Sanitize error messages. |
| **Low** | Error String in Logs | `crypto/signer.py:89` | `error=str(e)` on verification failure may leak exception details. Log error type only. |
| **Low** | Wallet Address in Startup Logs | `main.py:13` | `print(f"[Clawforge] Wallet: {settings.CLAW_EARN_WALLET}")` prints wallet to stdout. Remove or gate behind debug flag. |
| **Low** | Duplicate Model Definitions | `models.py:84,162,265,285` | `LedgerEntry`, `AuditEntry`, `SettlementStatement` each defined twice with different schemas. Consolidate to avoid import confusion. |

## Recommendations

1. **Immediate**: Add API authentication (API key or JWT) and rate limiting to `api/routes.py` before any production deployment.
2. **Immediate**: Sanitize `hash_file_content()` input - resolve path, verify it's within an allowed directory, and reject traversal sequences (`..`).
3. **Short-term**: Replace the TOCTOU read-modify-write in `ledger.py` with file-locked append operations or a database.
4. **Short-term**: Fix the trust boundary hostname check in `trust.py` to reject `evil-aiagentstore.ai` style subdomains.
5. **Short-term**: Add `CORSMiddleware` to `main.py` with explicit allowed origins.
6. **Medium-term**: Implement proper memory zeroization for decrypted private keys using `bytearray` or `ctypes`.
7. **Medium-term**: Remove dead code in `credentials.py:73` and consolidate duplicate model definitions in `models.py`.
8. **Low-priority**: Sanitize logged error messages across crypto modules to avoid leaking implementation details.

## Files Scanned

- `src/clawforge/crypto/signer.py` - EIP-191 signing (clean)
- `src/clawforge/crypto/vault.py` - AES-256-GCM vault (memory zeroization issue)
- `src/clawforge/crypto/hasher.py` - SHA-256/Keccak-256 (path traversal)
- `src/clawforge/protocol/trust.py` - HTTPS trust boundary (subdomain spoofing)
- `src/clawforge/protocol/loader.py` - Protocol fetch/cache (clean, atomic writes)
- `src/clawforge/auth/wallet.py` - Wallet management (clean)
- `src/clawforge/auth/credentials.py` - Credential scoping (dead code bug)
- `src/clawforge/sentinel/watcher.py` - Watchdog (clean, atomic writes)
- `src/clawforge/economy/ledger.py` - USDC ledger (TOCTOU race)
- `src/clawforge/economy/staker.py` - Auto-staker (clean, atomic writes)
- `src/clawforge/api/routes.py` - API endpoints (no auth, no rate limiting, no input validation)
- `src/clawforge/main.py` - FastAPI app (no CORS, wallet in logs)
- `src/clawforge/config.py` - Settings (clean, env-based)
- `requirements.txt` - Dependencies (no known critical CVEs)
