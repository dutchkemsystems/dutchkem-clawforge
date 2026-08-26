# Semantic Memories

<!-- id: sem-001 -->
- **Atomic Writes**: Use atomic writes (temp+rename) for all file-based storage to prevent corruption under concurrent access. Pattern: write to .tmp file, then rename to target. Essential for multi-process environments.

<!-- id: sem-002 -->
- **Async Scheduler**: Use AsyncIOScheduler for APScheduler in async FastAPI contexts to avoid false Dead Man's Switch triggers. Sync scheduler in async context causes heartbeat stalls.

<!-- id: sem-003 -->
- **HTTPS Trust Boundary**: HTTPS Trust Boundary must intercept HTTP redirect chains, not just validate initial URLs. HTTP->HTTPS redirects can bypass trust checks if only initial URL is validated.

<!-- id: sem-004 -->
- **API Authentication**: Implement API authentication (API key/JWT) and rate limiting for production FastAPI deployments. All endpoints publicly exposed is a critical security vulnerability.

<!-- id: sem-005 -->
- **Hash Chain Integrity**: Hash-chained audit logs are fragile - validate chain integrity at each entry insertion. One corrupted entry invalidates all subsequent entries in the chain.
