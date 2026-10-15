"""Tests for the Sentry integration module."""

import os
from unittest import mock

from clawforge import observability


def test_init_sentry_is_noop_without_dsn(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    observability._initialized = False
    assert observability.init_sentry() is False
    assert observability._initialized is False


def test_init_sentry_is_noop_with_empty_dsn(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "   ")
    observability._initialized = False
    assert observability.init_sentry() is False


def test_init_sentry_handles_import_error(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "https://example.invalid/1")
    observability._initialized = False
    with mock.patch.dict("sys.modules", {"sentry_sdk": None}):
        # Should not raise even if sentry_sdk cannot be imported
        observability.init_sentry()
