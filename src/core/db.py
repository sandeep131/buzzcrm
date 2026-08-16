"""Database engine, session factory, and declarative base.

Engine and session factory are built lazily so that importing this module
does not require DATABASE_URL to be set (matters for tooling and tests).

Sync SQLAlchemy — see the sync/async note in README.md. Pending ADR-010.
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base. All models inherit from this.

    Base audit/tenant fields arrive in issue #2 as a mixin, not here.
    """


@lru_cache
def get_engine() -> Engine:
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        future=True,
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        expire_on_commit=False,
    )


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a database session.

    Tenant and soft-delete scoping are NOT applied here — they arrive in
    issue #3 via the repository base, which is the only correct place for
    them (ADR-006, ADR-009).
    """
    with get_session_factory()() as session:
        yield session
