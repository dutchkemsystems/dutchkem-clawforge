import httpx
import json
import os

API_KEY = os.environ.get("RENDER_API_KEY", "")
if not API_KEY:
    raise ValueError("RENDER_API_KEY environment variable is required")
headers = {"Authorization": f"Bearer {API_KEY}"}

# List services
r = httpx.get("https://api.render.com/v1/services", headers=headers, timeout=15)
services = r.json()

for s in services:
    svc = s["service"]
    details = svc.get("serviceDetails", {})
    print(f"Name: {svc['name']}")
    print(f"ID: {svc['id']}")
    print(f"Repo: {svc.get('repo', 'none')}")
    print(f"Branch: {svc.get('branch', 'none')}")
    print(f"URL: {details.get('url', 'not deployed yet')}")
    print(f"Plan: {details.get('buildPlan', 'unknown')}")
    print("---")

# Check env vars for the service
if services:
    svc_id = services[0]["service"]["id"]
    r2 = httpx.get(f"https://api.render.com/v1/services/{svc_id}/env-vars", headers=headers, timeout=15)
    env_vars = r2.json()
    print("ENV VARS:")
    for ev in env_vars:
        key = ev.get("key", "")
        # Don't print secret values
        if "KEY" in key or "SECRET" in key or "PRIVATE" in key:
            print(f"  {key}: ***SET***" if ev.get("value") else f"  {key}: NOT SET")
        else:
            print(f"  {key}: {ev.get('value', 'NOT SET')}")
