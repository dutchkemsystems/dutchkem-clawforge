"""Error tracking integration. No-op when SENTRY_DSN is unset."""

from __future__ import annotations

import os

import structlog

log = structlog.get_logger(__name__)

_initialized = False


def init_sentry(dsn: str | None = None) -> bool:
    """
    Initialize Sentry if a DSN is available.

    Returns True if Sentry was initialized, False otherwise. Never raises.
    """
    global _initialized
    if _initialized:
        return True

    dsn = dsn or os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        log.info("sentry.disabled", reason="no_dsn")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=dsn,
            integrations=[StarletteIntegration(), FastApiIntegration()],
            traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            environment=os.environ.get("CLAW_ENV", "development"),
            send_default_pii=False,
        )
        _initialized = True
        log.info("sentry.initialized", environment=os.environ.get("CLAW_ENV", "development"))
        return True
    except Exception as exc:  # noqa: BLE001 — never fail app start over telemetry
        log.error("sentry.init_failed", error=str(exc))
        return False
