import httpx
import json
import os
import time

API_KEY = os.environ.get("RENDER_API_KEY", "")
if not API_KEY:
    raise ValueError("RENDER_API_KEY environment variable is required")
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
SVC_ID = os.environ.get("RENDER_SERVICE_ID", "srv-da89d7142hec73c7lj1g")

# Step 1: Get current env vars
print("=== Step 1: Getting current env vars ===")
try:
    r = httpx.get(f"https://api.render.com/v1/services/{SVC_ID}/env-vars", headers=headers, timeout=30)
    current_env = r.json()
    print(f"Current env vars count: {len(current_env)}")
    for ev in current_env:
        key = ev.get("key", "")
        if "KEY" in key or "SECRET" in key or "PRIVATE" in key:
            print(f"  {key}: ***SET***")
        else:
            print(f"  {key}: {ev.get('value', 'NOT SET')}")
except Exception as e:
    print(f"Error getting env vars: {e}")

# Step 2: Set required env vars
print("\n=== Step 2: Setting env vars ===")
required_vars = {
    "CLAW_EARN_BASE_URL": "https://aiagentstore.ai",
    "SENTINEL_HEARTBEAT_INTERVAL": "60",
    "SENTINEL_FRESHNESS_THRESHOLD": "90",
    "SENTINEL_DEAD_MAN_SWITCH": "300",
    "AUTO_STAKE_PERCENTAGE": "0.10",
    "MAX_DAILY_STAKE_USDC": "1000.0",
}

for key, value in required_vars.items():
    try:
        r = httpx.post(
            f"https://api.render.com/v1/services/{SVC_ID}/env-vars",
            headers=headers,
            json={"key": key, "value": value},
            timeout=15,
        )
        if r.status_code in [200, 201]:
            print(f"  OK: {key}={value}")
        else:
            print(f"  FAIL ({r.status_code}): {key} - {r.text[:100]}")
    except Exception as e:
        print(f"  ERROR: {key} - {e}")

# Step 3: Trigger manual deploy
print("\n=== Step 3: Triggering deploy ===")
try:
    r = httpx.post(
        f"https://api.render.com/v1/services/{SVC_ID}/deploys",
        headers=headers,
        json={"clear_cache": "false"},
        timeout=30,
    )
    if r.status_code in [200, 201]:
        deploy = r.json()
        print(f"Deploy triggered! ID: {deploy.get('id', 'unknown')}")
        print(f"Status: {deploy.get('status', 'unknown')}")
    else:
        print(f"Deploy failed ({r.status_code}): {r.text[:200]}")
except Exception as e:
    print(f"Deploy error: {e}")

print("\n=== Done ===")
