"""
Test fixtures and configuration for Signal Hunter tests.

Provides:
- Test settings with overrides for CI/testing
- FastAPI test client
- Mock services for unit tests
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _set_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure test environment variables are set."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    # Set dummy values for required fields so Settings validates in CI
    monkeypatch.setenv("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY", "sk-test-key"))
    monkeypatch.setenv("SUPABASE_URL", os.getenv("SUPABASE_URL", "https://test.supabase.co"))
    monkeypatch.setenv("SUPABASE_ANON_KEY", os.getenv("SUPABASE_ANON_KEY", "test-anon-key"))
    monkeypatch.setenv(
        "SUPABASE_SERVICE_ROLE_KEY",
        os.getenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key"),
    )
    monkeypatch.setenv(
        "UPSTASH_REDIS_REST_URL", os.getenv("UPSTASH_REDIS_REST_URL", "https://test.upstash.io")
    )
    monkeypatch.setenv(
        "UPSTASH_REDIS_REST_TOKEN", os.getenv("UPSTASH_REDIS_REST_TOKEN", "test-token")
    )


@pytest.fixture
def test_client() -> TestClient:
    """FastAPI test client for integration tests."""
    # Clear cached settings to pick up test env vars
    from app.config import get_settings
    get_settings.cache_clear()

    from app.main import create_app
    app = create_app()
    return TestClient(app)
