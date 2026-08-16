"""Shared pytest fixtures.

DATABASE_URL is set before app modules are imported so that settings load
without requiring a developer .env during unit tests.
"""

import os

import pytest

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://buzzcrm:buzzcrm@localhost:5433/buzzcrm_test",
)
os.environ.setdefault("ENVIRONMENT", "test")

from fastapi.testclient import TestClient  # noqa: E402

from src.main import create_app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    """Client for tests that do not touch the database.

    A database-backed session fixture arrives in issue #2, once there is
    a schema to create. Tenant-scoped fixtures arrive in issue #3.
    """
    return TestClient(create_app())
