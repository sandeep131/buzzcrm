"""Issue #3 acceptance — request scope and repository base.

The acceptance criterion is adversarial: "a query through the base class cannot
return another tenant's rows or soft-deleted rows without an explicit override,
proven by test."

These tests therefore try to *break* isolation rather than confirm it works in
the easy case. A missing tenant predicate is a cross-customer data leak, so the
interesting cases are direct-ID fetches, updates, and deletes aimed across a
tenant boundary — not just list endpoints.

The full per-endpoint sweep lands in #8; this proves the layer they all rest on.
"""

import uuid

import pytest
from sqlalchemy.orm import Session

from src.core.repository import TenantScopedRepository, UserRepository
from src.core.scope import (
    RequestScope,
    SystemActorAuthenticationError,
    get_current_user,
    resolve_stub_user,
)
from src.models.seed import provision_tenant
from src.models.tenant import Tenant
from src.models.user import User


@pytest.fixture
def two_tenants(db_session: Session):
    """Two fully-populated tenants — the shape every isolation test needs.

    Returns (scope_a, scope_b, alice, bob) where alice is in A and bob in B.
    """
    tenant_a, system_a = provision_tenant(db_session, name="Alpha", slug="alpha")
    tenant_b, system_b = provision_tenant(db_session, name="Beta", slug="beta")
    db_session.commit()

    alice = User(
        tenant_id=tenant_a.id,
        email="alice@alpha.test",
        display_name="Alice",
        created_by=system_a.id,
        updated_by=system_a.id,
    )
    bob = User(
        tenant_id=tenant_b.id,
        email="bob@beta.test",
        display_name="Bob",
        created_by=system_b.id,
        updated_by=system_b.id,
    )
    db_session.add_all([alice, bob])
    db_session.commit()

    return (
        RequestScope(user=alice, tenant=tenant_a),
        RequestScope(user=bob, tenant=tenant_b),
        alice,
        bob,
    )


# --- Invariant 1: tenant isolation -----------------------------------------


def test_list_excludes_other_tenants_rows(db_session: Session, two_tenants) -> None:
    scope_a, _scope_b, alice, bob = two_tenants
    repo = UserRepository(db_session, scope_a)

    listed = repo.list()
    ids = {u.id for u in listed}

    assert alice.id in ids
    assert bob.id not in ids


def test_other_tenants_row_is_unfetchable_by_direct_id(
    db_session: Session, two_tenants
) -> None:
    """ADR-006's non-negotiable test. Knowing the UUID must not be enough.

    Returns None rather than raising: a row in another tenant must be
    indistinguishable from one that does not exist, or the error itself
    confirms which ids are real.
    """
    scope_a, _scope_b, _alice, bob = two_tenants
    repo = UserRepository(db_session, scope_a)

    assert repo.get(bob.id) is None
    assert repo.get(bob.id, include_deleted=True) is None


def test_other_tenants_row_is_unupdatable(db_session: Session, two_tenants) -> None:
    scope_a, _scope_b, _alice, bob = two_tenants
    repo = UserRepository(db_session, scope_a)

    assert repo.update(bob.id, display_name="Hijacked") is None

    db_session.commit()
    db_session.refresh(bob)
    assert bob.display_name == "Bob"


def test_other_tenants_row_is_undeletable(db_session: Session, two_tenants) -> None:
    scope_a, _scope_b, _alice, bob = two_tenants
    repo = UserRepository(db_session, scope_a)

    assert repo.soft_delete(bob.id) is None

    db_session.commit()
    db_session.refresh(bob)
    assert bob.deleted_at is None


def test_count_is_tenant_scoped(db_session: Session, two_tenants) -> None:
    scope_a, scope_b, _alice, _bob = two_tenants

    assert UserRepository(db_session, scope_a).count() == 1
    assert UserRepository(db_session, scope_b).count() == 1


def test_create_forces_the_scopes_tenant(db_session: Session, two_tenants) -> None:
    """A caller must not be able to plant a row in another tenant."""
    scope_a, _scope_b, _alice, bob = two_tenants
    repo = UserRepository(db_session, scope_a)

    created = repo.create(
        email="planted@alpha.test",
        display_name="Planted",
        tenant_id=bob.tenant_id,  # ignored
    )
    db_session.commit()

    assert created.tenant_id == scope_a.tenant_id


def test_create_forces_the_scopes_actor(db_session: Session, two_tenants) -> None:
    """Authorship comes from the request, not from the caller's payload."""
    scope_a, _scope_b, _alice, bob = two_tenants
    repo = UserRepository(db_session, scope_a)

    created = repo.create(
        email="attributed@alpha.test",
        display_name="Attributed",
        created_by=bob.id,  # ignored
        updated_by=bob.id,  # ignored
    )
    db_session.commit()

    assert created.created_by == scope_a.user_id
    assert created.updated_by == scope_a.user_id


def test_update_cannot_move_a_row_between_tenants(
    db_session: Session, two_tenants
) -> None:
    scope_a, _scope_b, alice, bob = two_tenants
    repo = UserRepository(db_session, scope_a)

    repo.update(alice.id, tenant_id=bob.tenant_id, display_name="Renamed")
    db_session.commit()
    db_session.refresh(alice)

    assert alice.tenant_id == scope_a.tenant_id
    assert alice.display_name == "Renamed"


def test_there_is_no_cross_tenant_keyword(db_session: Session, two_tenants) -> None:
    """ADR-006 c.5 is enforced by the API's shape.

    No argument widens tenant scope, so cross-tenant access is not merely
    discouraged — it cannot be expressed. Asserted so that adding such an
    argument breaks a test rather than passing review quietly.
    """
    scope_a, _scope_b, _alice, _bob = two_tenants
    repo = UserRepository(db_session, scope_a)

    with pytest.raises(TypeError):
        repo.list(include_other_tenants=True)

    with pytest.raises(TypeError):
        repo.list(tenant_id=uuid.uuid4())


# --- Invariant 2: soft delete ----------------------------------------------


def test_soft_deleted_rows_are_hidden(db_session: Session, two_tenants) -> None:
    scope_a, _scope_b, alice, _bob = two_tenants
    repo = UserRepository(db_session, scope_a)

    repo.soft_delete(alice.id)
    db_session.commit()

    assert repo.get(alice.id) is None
    assert alice.id not in {u.id for u in repo.list()}
    assert repo.count() == 0


def test_include_deleted_reveals_them(db_session: Session, two_tenants) -> None:
    """The bypass #10 needs — re-import must see soft-deleted rows to stay
    idempotent (ADR-009)."""
    scope_a, _scope_b, alice, _bob = two_tenants
    repo = UserRepository(db_session, scope_a)

    repo.soft_delete(alice.id)
    db_session.commit()

    assert repo.get(alice.id, include_deleted=True) is not None
    assert alice.id in {u.id for u in repo.list(include_deleted=True)}
    assert repo.count(include_deleted=True) == 1


def test_include_deleted_does_not_widen_tenant_scope(
    db_session: Session, two_tenants
) -> None:
    """The bypass must relax exactly one predicate, not all of them.

    This is the failure mode worth guarding: an escape hatch that quietly
    drops the tenant filter along with the delete filter.
    """
    scope_a, scope_b, _alice, bob = two_tenants

    UserRepository(db_session, scope_b).soft_delete(bob.id)
    db_session.commit()

    repo_a = UserRepository(db_session, scope_a)
    assert bob.id not in {u.id for u in repo_a.list(include_deleted=True)}
    assert repo_a.get(bob.id, include_deleted=True) is None


def test_soft_delete_records_actor_and_keeps_the_row(
    db_session: Session, two_tenants
) -> None:
    """ADR-009 — the record stays resolvable so its audit entries still point
    at something."""
    scope_a, _scope_b, alice, _bob = two_tenants
    repo = UserRepository(db_session, scope_a)

    deleted = repo.soft_delete(alice.id)
    db_session.commit()

    assert deleted.deleted_at is not None
    assert deleted.deleted_by == scope_a.user_id
    assert db_session.get(User, alice.id) is not None


def test_redeleting_is_a_noop(db_session: Session, two_tenants) -> None:
    scope_a, _scope_b, alice, _bob = two_tenants
    repo = UserRepository(db_session, scope_a)

    first = repo.soft_delete(alice.id)
    db_session.commit()
    first_timestamp = first.deleted_at

    assert repo.soft_delete(alice.id) is None

    db_session.commit()
    db_session.refresh(alice)
    assert alice.deleted_at == first_timestamp


# --- Invariant 3: system actor exclusion (ADR-011) -------------------------


def test_system_actor_is_excluded_from_listings(
    db_session: Session, two_tenants
) -> None:
    scope_a, _scope_b, _alice, _bob = two_tenants
    repo = UserRepository(db_session, scope_a)

    assert all(not u.is_system for u in repo.list())


def test_include_system_reveals_it(db_session: Session, two_tenants) -> None:
    scope_a, _scope_b, _alice, _bob = two_tenants
    repo = UserRepository(db_session, scope_a)

    assert any(u.is_system for u in repo.list(include_system=True))


def test_system_actor_still_resolves_by_id(db_session: Session, two_tenants) -> None:
    """Invariant 3 is narrower than 1 and 2 — it applies to listing only.

    An audit entry's actor must always resolve, or the UI cannot render
    "Imported by System" (ADR-011).
    """
    scope_a, _scope_b, _alice, _bob = two_tenants
    repo = UserRepository(db_session, scope_a)

    system_actor = next(u for u in repo.list(include_system=True) if u.is_system)

    assert repo.get(system_actor.id) is not None


def test_include_system_does_not_widen_tenant_scope(
    db_session: Session, two_tenants
) -> None:
    scope_a, scope_b, _alice, _bob = two_tenants

    listed_a = UserRepository(db_session, scope_a).list(include_system=True)

    assert all(u.tenant_id == scope_a.tenant_id for u in listed_a)
    assert len(listed_a) == 2  # alice + tenant A's system actor only


# --- The scope itself ------------------------------------------------------


def test_stub_resolves_seeded_user_and_tenant(db_session: Session) -> None:
    tenant, system_actor = provision_tenant(db_session, name="Stub", slug="stub")
    from src.models.seed import create_user

    create_user(
        db_session,
        tenant=tenant,
        actor=system_actor,
        email="sales@skyscape.com",
        display_name="Sales",
    )
    db_session.commit()

    scope = resolve_stub_user(db_session)

    assert scope.user.email == "sales@skyscape.com"
    assert scope.tenant.id == tenant.id
    assert scope.user.is_system is False


def test_stub_rejects_a_system_actor(db_session: Session) -> None:
    """ADR-011 — a system actor must never become an authenticated principal.

    Simulates the misconfiguration the SSO adapter must also refuse.
    """
    tenant, system_actor = provision_tenant(db_session, name="Sys", slug="sys")
    system_actor.email = "sales@skyscape.com"
    db_session.commit()

    with pytest.raises(SystemActorAuthenticationError):
        resolve_stub_user(db_session)


def test_scope_is_frozen(db_session: Session, two_tenants) -> None:
    """A live request must not be repointable at another tenant."""
    scope_a, _scope_b, _alice, _bob = two_tenants

    with pytest.raises(Exception):
        scope_a.tenant = _scope_b.tenant


# --- Wiring through FastAPI ------------------------------------------------


def test_dependency_resolves_through_fastapi(db_session: Session) -> None:
    """`get_current_user` must work as a real Depends(), not just as a call.

    No route uses it yet — endpoints arrive in #5 and #7 — so this mounts a
    throwaway route to prove the dependency chain (session -> scope) resolves
    inside a request. Without it, the wiring stays unproven until #5.
    """
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    tenant, system_actor = provision_tenant(db_session, name="Wired", slug="wired")
    from src.models.seed import create_user

    create_user(
        db_session,
        tenant=tenant,
        actor=system_actor,
        email="sales@skyscape.com",
        display_name="Sales",
    )
    db_session.commit()

    app = FastAPI()

    @app.get("/whoami")
    def whoami(scope: RequestScope = Depends(get_current_user)) -> dict:
        return {
            "email": scope.user.email,
            "tenant": scope.tenant.slug,
            "is_system": scope.user.is_system,
        }

    response = TestClient(app).get("/whoami")

    assert response.status_code == 200
    assert response.json() == {
        "email": "sales@skyscape.com",
        "tenant": "wired",
        "is_system": False,
    }


def test_dependency_401s_when_unseeded(db_session: Session) -> None:
    """An empty database must produce a clean 401, not a 500."""
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    @app.get("/whoami")
    def whoami(scope: RequestScope = Depends(get_current_user)) -> dict:
        return {"email": scope.user.email}

    response = TestClient(app).get("/whoami")

    assert response.status_code == 401
    assert "seed" in response.json()["detail"]


# --- Guarding the base class itself ----------------------------------------


def test_repository_refuses_a_model_without_tenant_id(db_session: Session) -> None:
    """`tenants` has no tenant_id and must not be reachable through this class.

    Failing at construction beats silently returning unscoped rows.
    """

    class TenantRepository(TenantScopedRepository[Tenant]):
        model = Tenant

    scope = RequestScope(user=None, tenant=None)

    with pytest.raises(TypeError, match="cannot be managed"):
        TenantRepository(db_session, scope)


def test_create_cannot_write_a_born_deleted_row(
    db_session: Session, two_tenants
) -> None:
    """Lifecycle fields are scope-controlled — a create cannot forge a delete."""
    from datetime import datetime, timezone

    scope_a, _scope_b, _alice, _bob = two_tenants
    repo = UserRepository(db_session, scope_a)

    created = repo.create(
        email="born-deleted@alpha.test",
        display_name="Born Deleted",
        deleted_at=datetime.now(timezone.utc),  # ignored
    )
    db_session.commit()

    assert created.deleted_at is None
    assert repo.get(created.id) is not None


def test_update_cannot_silently_undelete(db_session: Session, two_tenants) -> None:
    """Restoring is a real operation, but it needs its own method rather than
    arriving as an incidental field update."""
    scope_a, _scope_b, alice, _bob = two_tenants
    repo = UserRepository(db_session, scope_a)

    repo.soft_delete(alice.id)
    db_session.commit()

    # Not visible, so not updatable at all — the delete filter does the work.
    assert repo.update(alice.id, deleted_at=None) is None

    db_session.commit()
    db_session.refresh(alice)
    assert alice.deleted_at is not None
