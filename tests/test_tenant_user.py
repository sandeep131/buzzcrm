"""Issue #2 acceptance — Tenant and User models, and the ADR-011 system actor.

Covers the acceptance criteria in ops/ISSUES.md #2 (migration applies and
downgrades, seed produces a usable tenant + user, models match
DOMAIN_MODEL.md) and the testing requirements in ADR-011.
"""

import uuid
from datetime import datetime, timezone

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.db import get_engine
from src.models.seed import provision_tenant, seed_development_data
from src.models.tenant import Tenant
from src.models.user import User


# --- Seeding and the system actor -----------------------------------------


def test_seed_produces_tenant_system_actor_and_human(db_session: Session) -> None:
    tenant, system_actor, human = seed_development_data(db_session)
    db_session.commit()

    assert tenant.id is not None
    assert tenant.slug == "skyscape"

    assert system_actor.is_system is True
    assert system_actor.tenant_id == tenant.id

    assert human.is_system is False
    assert human.tenant_id == tenant.id


def test_bootstrap_commits_with_deferred_constraints(db_session: Session) -> None:
    """The circular reference must survive an actual COMMIT.

    tenants.created_by -> users and users.tenant_id -> tenants point at each
    other, so this only works because the actor FKs are DEFERRABLE INITIALLY
    DEFERRED. A flush alone would not prove it; the check happens at commit.
    """
    tenant, system_actor = provision_tenant(
        db_session, name="Bootstrap", slug="bootstrap"
    )
    db_session.commit()

    assert tenant.created_by == system_actor.id
    assert system_actor.tenant_id == tenant.id


def test_system_actor_created_by_resolves_to_itself(db_session: Session) -> None:
    """ADR-011 constraint 1 — no NULL is written, not even transiently."""
    _tenant, system_actor = provision_tenant(db_session, name="Self", slug="self")
    db_session.commit()

    assert system_actor.created_by == system_actor.id
    assert system_actor.updated_by == system_actor.id

    resolved = db_session.get(User, system_actor.created_by)
    assert resolved is system_actor


def test_exactly_one_system_actor_per_tenant(db_session: Session) -> None:
    tenant, _actor = provision_tenant(db_session, name="Solo", slug="solo")
    db_session.commit()

    actors = db_session.scalars(
        select(User).where(User.tenant_id == tenant.id, User.is_system.is_(True))
    ).all()

    assert len(actors) == 1


def test_second_system_actor_violates_unique_index(db_session: Session) -> None:
    """ADR-011 constraint 3 — enforced by the database, not by review."""
    tenant, _actor = provision_tenant(db_session, name="Dup", slug="dup")
    db_session.commit()

    db_session.add(
        User(
            tenant_id=tenant.id,
            email="second-system@buzzcrm.internal",
            display_name="Second System",
            is_system=True,
            created_by=_actor.id,
            updated_by=_actor.id,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_each_tenant_gets_its_own_system_actor(db_session: Session) -> None:
    """Per-tenant, never global (ADR-011). No cross-tenant reference exists."""
    tenant_a, actor_a = provision_tenant(db_session, name="A", slug="tenant-a")
    tenant_b, actor_b = provision_tenant(db_session, name="B", slug="tenant-b")
    db_session.commit()

    assert actor_a.id != actor_b.id
    assert actor_a.tenant_id == tenant_a.id
    assert actor_b.tenant_id == tenant_b.id

    # The system actor email repeats across tenants — which is only legal
    # because uniqueness is per tenant, and is the point of per-tenant actors.
    assert actor_a.email == actor_b.email

    # Every actor pointer stays inside its own tenant.
    assert db_session.get(User, tenant_a.created_by).tenant_id == tenant_a.id
    assert db_session.get(User, tenant_b.created_by).tenant_id == tenant_b.id


def test_seeding_is_idempotent(db_session: Session) -> None:
    first_tenant, first_actor, first_human = seed_development_data(db_session)
    db_session.commit()

    second_tenant, second_actor, second_human = seed_development_data(db_session)
    db_session.commit()

    assert second_tenant.id == first_tenant.id
    assert second_actor.id == first_actor.id
    assert second_human.id == first_human.id

    assert len(db_session.scalars(select(Tenant)).all()) == 1
    assert len(db_session.scalars(select(User)).all()) == 2


# --- Constraints -----------------------------------------------------------


def test_created_by_rejects_null(db_session: Session) -> None:
    """created_by is total — that is what the system actor buys (ADR-011)."""
    tenant, actor = provision_tenant(db_session, name="NotNull", slug="notnull")
    db_session.commit()

    db_session.add(
        User(
            tenant_id=tenant.id,
            email="nulled@example.com",
            display_name="Nulled",
            created_by=None,
            updated_by=actor.id,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_user_tenant_id_must_reference_a_real_tenant(db_session: Session) -> None:
    _tenant, actor = provision_tenant(db_session, name="FK", slug="fk")
    db_session.commit()

    db_session.add(
        User(
            tenant_id=uuid.uuid4(),  # no such tenant
            email="ghost@example.com",
            display_name="Ghost",
            created_by=actor.id,
            updated_by=actor.id,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_email_is_unique_per_tenant_not_globally(db_session: Session) -> None:
    """ADR-006 applies the same per-tenant logic to sf_id.

    Two tenants may legitimately hold the same person.
    """
    tenant_a, actor_a = provision_tenant(db_session, name="A", slug="email-a")
    tenant_b, actor_b = provision_tenant(db_session, name="B", slug="email-b")
    db_session.commit()

    shared = "same.person@example.com"
    db_session.add(
        User(
            tenant_id=tenant_a.id,
            email=shared,
            display_name="In A",
            created_by=actor_a.id,
            updated_by=actor_a.id,
        )
    )
    db_session.add(
        User(
            tenant_id=tenant_b.id,
            email=shared,
            display_name="In B",
            created_by=actor_b.id,
            updated_by=actor_b.id,
        )
    )
    db_session.commit()  # legal — different tenants

    duplicate = User(
        tenant_id=tenant_a.id,
        email=shared,
        display_name="Duplicate in A",
        created_by=actor_a.id,
        updated_by=actor_a.id,
    )
    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_soft_deleted_email_can_be_reused(db_session: Session) -> None:
    """ADR-009 constraint 2 — the partial index trap.

    A plain unique index would reject this, because the soft-deleted row still
    physically exists.
    """
    tenant, actor = provision_tenant(db_session, name="Reuse", slug="reuse")
    db_session.commit()

    original = User(
        tenant_id=tenant.id,
        email="recycled@example.com",
        display_name="Original",
        created_by=actor.id,
        updated_by=actor.id,
    )
    db_session.add(original)
    db_session.commit()

    original.deleted_at = datetime.now(timezone.utc)
    original.deleted_by = actor.id
    db_session.commit()

    db_session.add(
        User(
            tenant_id=tenant.id,
            email="recycled@example.com",
            display_name="Replacement",
            created_by=actor.id,
            updated_by=actor.id,
        )
    )
    db_session.commit()  # must not raise

    live = db_session.scalars(
        select(User).where(
            User.email == "recycled@example.com", User.deleted_at.is_(None)
        )
    ).all()
    assert len(live) == 1
    assert live[0].display_name == "Replacement"


def test_soft_deleted_tenant_slug_can_be_reused(db_session: Session) -> None:
    tenant, actor = provision_tenant(db_session, name="Slug", slug="recycled-slug")
    db_session.commit()

    tenant.deleted_at = datetime.now(timezone.utc)
    tenant.deleted_by = actor.id
    db_session.commit()

    replacement, _actor = provision_tenant(
        db_session, name="Slug Again", slug="recycled-slug"
    )
    db_session.commit()  # must not raise

    assert replacement.id != tenant.id


# --- Schema shape matches DOMAIN_MODEL.md ----------------------------------


def test_tenants_has_no_tenant_id_column() -> None:
    """The one carve-out to ADR-006 — tenants IS the scope (ADR-011).

    Asserted so a future contributor does not "fix" the apparent omission.
    """
    columns = {c["name"] for c in inspect(get_engine()).get_columns("tenants")}

    assert "tenant_id" not in columns


def test_users_is_tenant_scoped() -> None:
    """Every table except tenants obeys ADR-006 without exception."""
    columns = {c["name"] for c in inspect(get_engine()).get_columns("users")}

    assert "tenant_id" in columns


@pytest.mark.parametrize("table", ["tenants", "users"])
def test_base_audit_fields_present(table: str) -> None:
    """DOMAIN_MODEL.md, "Base Fields — Every Domain Table"."""
    columns = {c["name"] for c in inspect(get_engine()).get_columns(table)}

    assert {
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "deleted_at",
        "deleted_by",
    } <= columns


@pytest.mark.parametrize("table", ["tenants", "users"])
def test_not_salesforce_sourced(table: str) -> None:
    """Neither tenants nor users is imported from Salesforce, so neither
    carries sf_id. Issue #5 onward add it to the entities that are."""
    columns = {c["name"] for c in inspect(get_engine()).get_columns(table)}

    assert "sf_id" not in columns


def test_domain_model_fields_present() -> None:
    tenant_columns = {c["name"] for c in inspect(get_engine()).get_columns("tenants")}
    user_columns = {c["name"] for c in inspect(get_engine()).get_columns("users")}

    assert {"name", "slug", "is_active"} <= tenant_columns
    assert {"tenant_id", "email", "display_name", "is_active"} <= user_columns


# --- Rule 4: migrations are reversible -------------------------------------


def test_migration_downgrades_and_reapplies(alembic_config: Config) -> None:
    """AGENTS.md rule 4. Leaves the database back at head for other tests.

    The circular foreign keys make this the failure-prone direction: the
    downgrade must drop the constraints before the tables, or dropping `users`
    fails while `tenants` still references it.
    """
    command.downgrade(alembic_config, "base")

    remaining = set(inspect(get_engine()).get_table_names())
    assert "tenants" not in remaining
    assert "users" not in remaining

    command.upgrade(alembic_config, "head")

    restored = set(inspect(get_engine()).get_table_names())
    assert {"tenants", "users"} <= restored
