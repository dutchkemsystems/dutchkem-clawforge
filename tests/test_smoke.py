"""Live API smoke tests — run after uvicorn is up on :8766."""
import httpx, json, sys

BASE = "http://127.0.0.1:8766"
passed = 0
failed = 0

client = httpx.Client(base_url=BASE, timeout=10)

def check(name, method, url, expected_status=None, expected_body=None):
    global passed, failed
    try:
        r = getattr(client, method)(url)
        ok = True
        if expected_status and r.status_code != expected_status:
            print(f"  FAIL {name}: expected status {expected_status}, got {r.status_code}")
            ok = False
        if expected_body:
            for k, v in expected_body.items():
                actual = r.json().get(k)
                if actual != v:
                    print(f"  FAIL {name}: expected {k}={v}, got {actual}")
                    ok = False
        if ok:
            print(f"  PASS {name} [{r.status_code}]")
            passed += 1
        else:
            failed += 1
    except Exception as e:
        print(f"  FAIL {name}: {e}")
        failed += 1

print("=== GET ENDPOINTS ===")
check("health", "get", "/v1/health", 200, {"status": "ok", "service": "clawforge"})
check("tasks list", "get", "/v1/tasks", 200)
check("tasks filter", "get", "/v1/tasks?status=FUNDED", 200)
check("task not found", "get", "/v1/tasks/nonexistent", 404)
check("ledger", "get", "/v1/ledger", 200)
check("ledger balance", "get", "/v1/ledger/balance", 200, {"currency": "USDC"})
check("audit log", "get", "/v1/audit", 200)
check("audit verify", "get", "/v1/audit/verify", 200, {"valid": True})
check("settlement 404", "get", "/v1/settlement/nonexistent", 404)
check("sentinel", "get", "/v1/sentinel/status", 200)
check("reputation", "get", "/v1/reputation", 200)
check("trust pending", "get", "/v1/trust/pending-approvals", 200)

print("\n=== POST ENDPOINTS ===")
check("bid task-1", "post", "/v1/tasks/task-1/bid?bid_amount=50.0", 200)
check("bid negative", "post", "/v1/tasks/task-1/bid?bid_amount=-10.0", 400)
check("submit proof", "post", "/v1/tasks/task-1/submit", 200)
check("reclaim stake", "post", "/v1/tasks/task-1/stake-reclaim", 200)
check("rate task", "post", "/v1/reputation/rate?task_id=task-1&rating=4.5", 200)
check("rate invalid", "post", "/v1/reputation/rate?task_id=task-1&rating=6.0", 400)
check("approve nonexistent", "post", "/v1/trust/approve/999", 404)
check("reject nonexistent", "post", "/v1/trust/reject/999", 404)

print("\n=== CHAINED OPERATIONS ===")
r = client.post("/v1/tasks/task-2/bid?bid_amount=25.0")
assert r.status_code == 200, f"bid failed: {r.status_code}"
r = client.post("/v1/tasks/task-2/submit")
assert r.status_code == 200, f"submit failed: {r.status_code}"
r = client.post("/v1/tasks/task-2/stake-reclaim")
assert r.status_code == 200, f"reclaim failed: {r.status_code}"
r = client.post("/v1/reputation/rate?task_id=task-2&rating=5.0")
assert r.status_code == 200, f"rate failed: {r.status_code}"
print("  PASS chained bid->submit->reclaim->rate")
passed += 1

r = client.get("/v1/ledger")
entries = r.json()["count"]
print(f"  PASS ledger has {entries} entries after operations")
passed += 1

r = client.get("/v1/audit/verify")
assert r.json()["valid"] is True
print("  PASS audit chain still valid")
passed += 1

r = client.post("/v1/tasks/task-1/bid?bid_amount=75.0")
assert r.status_code == 200
print("  PASS second bid on task-1")
passed += 1

r = client.get("/v1/tasks")
print(f"  PASS task list: {r.json()['count']} tasks")
passed += 1

client.close()
print(f"\n{'='*50}")
print(f"RESULTS: {passed} passed, {failed} failed, {passed+failed} total")
if failed > 0:
    sys.exit(1)
print("ALL TESTS PASSED")
