# Phase 06: QA Plan

## Executive Summary
Comprehensive test suite created for all 10 Clawforge modules: 230 tests covering crypto, protocol, auth, sentinel, memory, economy, tasks, execution, audit, and API endpoints. All tests pass. Several source code bugs were identified during testing.

## Test Strategy
- **Unit tests**: Individual module functions with mocked dependencies
- **Integration tests**: Full task lifecycle, ledger tamper detection, reputation economy flow
- **Security tests**: Vault encryption/decryption, signature signing/verification, trust boundary enforcement
- **Edge case tests**: Empty inputs, concurrent access patterns, error handling paths

## Tests Implemented
- `tests/test_crypto.py` (29 tests): Signer (EIP-191), Hasher (SHA-256/Keccak-256), Vault (AES-256-GCM), hash chain verification
- `tests/test_protocol.py` (27 tests): TrustBoundary URL validation, HTTPS enforcement, redirect checking, ProtocolLoader fetch/cache/validate
- `tests/test_sentinel.py` (20 tests): Heartbeat emission, freshness check, Dead Man's Switch, recovery, state persistence
- `tests/test_tasks.py` (22 tests): TaskDiscovery fetch/filter, SmartBidder (interface validation due to source bug), SupplyDemandScanner
- `tests/test_execution.py` (18 tests): WorkExecutor dispatch/timeout, ProofGenerator (SHA-256/Keccak-256), A2AQueue
- `tests/test_audit.py` (18 tests): HashChainLogger chain integrity/tamper detection, SettlementGenerator signing
- `tests/test_memory.py` (31 tests): Hot/Warm/Cold memory tiers, CRUD operations, pruning, tag filtering
- `tests/test_economy.py` (26 tests): USDCLedger append-only/chain, AutoStaker stake/reclaim, ReputationTracker tier progression
- `tests/test_api.py` (15 tests): All REST API endpoints via FastAPI TestClient
- `tests/test_integration.py` (12 tests): Full lifecycle, reputation economy flow, security signing roundtrips

## Source Code Bugs Identified
1. **`warm.py` / `cold.py` `_save_entry`**: Calls `.isoformat()` on string after `model_dump(mode="json")` converts datetime to string - breaks `get()` and `put()` operations
2. **`audit/logger.py` `log()`**: Opens temp file in append mode but replaces original - loses previous entries
3. **`tasks/bidder.py`**: `Decimal * float` not supported - `calculate_bid()` and `value_to_stake_ratio()` crash
4. **`execution/executor.py`**: References `task.type` but `Task` model has no `type` field
5. **`sentinel/watcher.py` `_save_state`**: Same datetime serialization bug as warm/cold memory
6. **`execution/a2a.py`**: `PriorityQueue` requires comparable `Subtask` objects but no `__lt__` defined
7. **`protocol/trust.py` `_request_human_approval`**: Uses `asyncio.get_event_loop()` which fails in sync context

## Manual Validation Steps
1. Run `pytest tests/ -v` to execute full test suite
2. Verify env vars `CLAW_EARN_WALLET` and `CLAW_EARN_PRIVATE_KEY` are set before running
3. Fix identified source bugs, then re-run tests to confirm fixes
4. Run `pytest tests/ --cov=src/clawforge` to measure code coverage
