"""Clawforge main application."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .api.routes import router
from .api.auth import APIKeyAuthMiddleware
from .api.ratelimit import RateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    print("[Clawforge] Starting up...")
    print(f"[Clawforge] Wallet: {settings.CLAW_EARN_WALLET[:10]}...")
    print(f"[Clawforge] Memory path: {settings.MEMORY_PATH}")

    for subdir in ["protocol", "memory/hot", "memory/warm", "memory/cold",
                   "economy", "tasks", "audit", "credentials", "sentinel", "config"]:
        Path(settings.MEMORY_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(f"./data/{subdir}").mkdir(parents=True, exist_ok=True)

    print("[Clawforge] All directories initialized.")
    print("[Clawforge] Ready to accept tasks.")

    yield

    print("[Clawforge] Shutting down gracefully...")


app = FastAPI(
    title="Dutchkem Ventures Clawforge",
    description="Autonomous Claw Earn Marketplace Integration Framework",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security middleware
settings = get_settings()
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)
app.add_middleware(APIKeyAuthMiddleware, api_key=settings.API_KEY)

# Routes
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("clawforge.main:app", host="0.0.0.0", port=8000, reload=True)
