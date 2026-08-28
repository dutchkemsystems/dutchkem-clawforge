"""Clawforge main application."""

import json
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.auth import APIKeyAuthMiddleware
from .api.ratelimit import RateLimitMiddleware
from .api.routes import router
from .config import get_settings
from .errors import ClawforgeError
from .events.bus import event_bus
from .sentinel.watcher import Sentinel


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    print("[Clawforge] Starting up...")
    print(f"[Clawforge] Wallet: {settings.CLAW_EARN_WALLET[:10]}...")
    print(f"[Clawforge] Memory path: {settings.MEMORY_PATH}")

    # Initialize data directories using config paths
    data_dirs = [
        settings.get_protocol_path(),
        settings.get_memory_path() / "hot",
        settings.get_memory_path() / "warm",
        settings.get_memory_path() / "cold",
        settings.get_economy_path(),
        settings.get_tasks_path(),
        settings.get_audit_path(),
        settings.get_credentials_path(),
        settings.get_sentinel_path(),
        settings.get_config_path(),
        Path("./data/settlement"),
    ]
    for data_dir in data_dirs:
        data_dir.mkdir(parents=True, exist_ok=True)

    print("[Clawforge] All directories initialized.")

    # Start Sentinel watchdog
    sentinel = Sentinel()
    await sentinel.start()
    app.state.sentinel = sentinel
    print("[Clawforge] Sentinel watchdog started.")

    print("[Clawforge] Ready to accept tasks.")

    yield

    # Stop Sentinel watchdog
    print("[Clawforge] Shutting down gracefully...")
    if hasattr(app.state, "sentinel"):
        await app.state.sentinel.stop()
        print("[Clawforge] Sentinel watchdog stopped.")


app = FastAPI(
    title="Dutchkem Ventures Clawforge",
    description=(
        "Autonomous Claw Earn Marketplace Integration Framework. "
        "Connects AI agents to paid USDC tasks on Base chain with "
        "EIP-191 signing, least-privilege credentials, and audit trails."
    ),
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# Exception handler for ClawforgeError
@app.exception_handler(ClawforgeError)
async def clawforge_error_handler(request: Request, exc: ClawforgeError):
    """Handle ClawforgeError and return structured JSON response."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


# CORS configuration
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security middleware
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)
app.add_middleware(APIKeyAuthMiddleware, api_key=settings.API_KEY)

# REST routes
app.include_router(router)


# WebSocket endpoints
@app.websocket("/ws/events")
async def ws_events(websocket: WebSocket, topic: str = "all"):
    """WebSocket endpoint for real-time task events.

    Connect to receive live events. Query param `topic` filters events
    (default: 'all' receives everything).
    """
    await event_bus.connect(websocket, topic)
    try:
        while True:
            data = await websocket.receive_text()
            # Client can send ping/pong or subscription changes
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong", "timestamp": time.time()}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        event_bus.disconnect(websocket, topic)


@app.get("/ws/events/history")
async def ws_events_history(limit: int = 50):
    """Get recent WebSocket event history."""
    events = event_bus.get_recent_events(limit)
    return {
        "events": [e.model_dump() for e in events],
        "count": len(events),
        "subscribers": event_bus.subscriber_count,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("clawforge.main:app", host="0.0.0.0", port=8000, reload=True)
