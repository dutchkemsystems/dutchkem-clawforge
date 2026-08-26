# Episodic Memories

<!-- id: epi-001 -->
- **TOCTOU Race Condition**: Ledger read-then-write allows data loss under concurrency. 
  - **Issue**: `economy/ledger.py:48-54` - Read-then-write on ledger file
  - **Fix**: Use file locking (fcntl.flock or filelock library) for concurrent access
  - **Impact**: Data loss in multi-process scenarios

<!-- id: epi-002 -->
- **Subdomain Spoofing**: endswith(ALLOWED_HOST) matches evil-aiagentstore.ai.
  - **Issue**: `protocol/trust.py:56` - hostname.endswith(ALLOWED_HOST) matches subdomains
  - **Fix**: Use `hostname == ALLOWED_HOST or hostname.endswith(f".{ALLOWED_HOST}")`
  - **Impact**: Security bypass allowing untrusted hosts

<!-- id: epi-003 -->
- **Ineffective Memory Zeroization**: decrypted = "0" * len(decrypted) fails because Python strings are immutable.
  - **Issue**: `crypto/vault.py:100-102` - String assignment doesn't zero memory
  - **Fix**: Use `bytearray` + explicit overwrite or `ctypes.memset`
  - **Impact**: Sensitive data may remain in memory

<!-- id: epi-004 -->
- **Dead Code Bug**: limit_path.with_suffix(".tmp") if False else ... - leftover ternary.
  - **Issue**: `auth/credentials.py:73` - Dead code from debugging
  - **Fix**: Remove the ternary condition entirely
  - **Impact**: Code confusion, potential logic errors
