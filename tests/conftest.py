"""Shared pytest fixtures.

DATABASE_URL is set before app modules are imported so that settings load
without requiring a developer .env during unit tests. It points at a *separate*
database (buzzcrm_test) — these fixtures drop and recreate the schema, which
must never touch the development database.
"""

import os

import pytest

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://buzzcrm:buzzcrm@localhost:5433/buzzcrm_test",
)
os.environ.setdefault("ENVIRONMENT", "test")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from src.core.db import get_engine  # noqa: E402
from src.main import create_app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    """Client for tests that do not touch the database.

    Tenant-scoped request fixtures arrive in issue #3 with get_current_user().
    """
    return TestClient(create_app())


@pytest.fixture(scope="session")
def alembic_config() -> Config:
    return Config("alembic.ini")


@pytest.fixture(scope="session")
def migrated_database(alembic_config: Config) -> None:
    """Build the schema once per test session, by running the real migrations.

    Deliberately migrations rather than `Base.metadata.create_all()`: the
    partial unique indexes and deferrable foreign keys are the things most
    worth testing, and a schema built from metadata would not prove the
    migration that production actually runs is correct.
    """
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")


@pytest.fixture
def db_session(migrated_database: None) -> Session:
    """A session that really commits, truncated between tests.

    The obvious harness — wrap each test in a transaction and roll it back —
    is wrong for this schema. Under that scheme `session.commit()` only
    releases a SAVEPOINT, and the actor foreign keys are DEFERRABLE INITIALLY
    DEFERRED, meaning Postgres defers them to real COMMIT. A deferred
    constraint would therefore never be checked: violations would pass
    silently, and the bootstrap tests would prove nothing while appearing to
    pass. That is worse than a slow suite.

    So tests commit for real and the tables are truncated afterwards. These
    tables are tiny; correctness is worth more than the milliseconds.
    """
    session = Session(bind=get_engine(), expire_on_commit=False)

    try:
        yield session
    finally:
        session.rollback()
        session.close()
        # Both tables in one statement — they reference each other, so
        # truncating them separately would trip the foreign keys.
        with get_engine().begin() as connection:
            connection.execute(text("TRUNCATE TABLE users, tenants CASCADE"))
