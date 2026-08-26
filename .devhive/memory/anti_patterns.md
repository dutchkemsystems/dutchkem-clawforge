# Anti-Pattern Memories

<!-- id: ant-001 -->
- **Secret Logging**: Don't print wallet addresses or secrets to stdout in production.
  - **Pattern**: `print(f"[Clawforge] Wallet: {settings.CLAW_EARN_WALLET}")`
  - **Why**: Secrets in logs can be captured by monitoring systems or log aggregation
  - **Better**: Use structured logging with debug flags, never log secrets

<!-- id: ant-002 -->
- **Exception Info Leakage**: Don't expose internal error details in exception messages.
  - **Pattern**: `VaultError(f"Decryption failed: {e}")` 
  - **Why**: Internal error details can reveal implementation specifics to attackers
  - **Better**: Sanitize error messages, log details separately at debug level

<!-- id: ant-003 -->
- **Hostname Validation Bypass**: Don't use endswith() for hostname validation without exact match.
  - **Pattern**: `hostname.endswith(ALLOWED_HOST)` matches `evil-aiagentstore.ai`
  - **Why**: Subdomains of untrusted hosts can bypass trust boundaries
  - **Better**: Exact match OR proper suffix check: `hostname == host or hostname.endswith(f".{host}")`

<!-- id: ant-004 -->
- **Duplicate Model Definitions**: Don't define duplicate Pydantic models.
  - **Pattern**: `LedgerEntry`, `AuditEntry`, `SettlementStatement` each defined twice
  - **Why**: Schema drift, import confusion, maintenance burden
  - **Better**: Consolidate to single source of truth, use imports for reusability
