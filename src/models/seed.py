"""Tenant provisioning and the Milestone 0 development seed.

`provision_tenant()` is the only correct way to create a tenant. A bare INSERT
produces a tenant with no system actor, and therefore a tenant whose machine
writes cannot be attributed (ADR-011, Consequences).

Run the development seed with:

    python -m src.models.seed

Placement note: this lives under `src/models/` because issue #2's module
boundary is `src/models/` + `migrations/`. It is provisioning logic rather than
a model, and should move to a CLI/scripts location once one exists.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.db import get_session_factory
from src.models.tenant import Tenant
from src.models.user import User

logger = logging.getLogger(__name__)

SYSTEM_ACTOR_EMAIL = "system@buzzcrm.internal"
SYSTEM_ACTOR_NAME = "System"


def provision_tenant(
    session: Session, *, name: str, slug: str
) -> tuple[Tenant, User]:
    """Create a tenant and its system actor in one transaction.

    Returns (tenant, system_actor). Does not commit — the caller owns the
    transaction boundary.

    The bootstrap is genuinely circular: the tenant needs a creator, and the
    creator needs a tenant. Both ids are generated here, application-side, so
    each row can reference the other before either is written. The actor FKs
    are DEFERRABLE INITIALLY DEFERRED, so Postgres checks them at COMMIT rather
    than per statement (ADR-011 constraint 2).

    The system actor's `created_by` points at itself. No NULL is ever written,
    not even transiently.
    """
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()

    tenant = Tenant(
        id=tenant_id,
        name=name,
        slug=slug,
        created_by=actor_id,
        updated_by=actor_id,
    )
    system_actor = User(
        id=actor_id,
        tenant_id=tenant_id,
        email=SYSTEM_ACTOR_EMAIL,
        display_name=SYSTEM_ACTOR_NAME,
        is_system=True,
        created_by=actor_id,  # self-referential by design
        updated_by=actor_id,
    )

    session.add(tenant)
    session.add(system_actor)
    session.flush()

    return tenant, system_actor


def create_user(
    session: Session,
    *,
    tenant: Tenant,
    actor: User,
    email: str,
    display_name: str,
) -> User:
    """Create an ordinary (non-system) user attributed to `actor`."""
    user = User(
        tenant_id=tenant.id,
        email=email,
        display_name=display_name,
        created_by=actor.id,
        updated_by=actor.id,
    )
    session.add(user)
    session.flush()
    return user


def seed_development_data(
    session: Session,
    *,
    tenant_slug: str = "skyscape",
    tenant_name: str = "Skyscape",
    user_email: str = "sales@skyscape.com",
    user_display_name: str = "Skyscape Sales",
) -> tuple[Tenant, User, User]:
    """Seed one tenant, its system actor, and one human user.

    Idempotent: re-running against an already-seeded database returns the
    existing rows rather than creating duplicates or raising. The human user is
    what the ADR-007 auth stub resolves to — never the system actor.

    Returns (tenant, system_actor, human_user).
    """
    existing = session.scalar(
        select(Tenant).where(Tenant.slug == tenant_slug, Tenant.deleted_at.is_(None))
    )

    if existing is not None:
        system_actor = session.scalar(
            select(User).where(
                User.tenant_id == existing.id,
                User.is_system.is_(True),
                User.deleted_at.is_(None),
            )
        )
        if system_actor is None:
            # Should be unreachable: provision_tenant() is the only way to
            # create a tenant and it always seeds an actor. If it happens, the
            # tenant's machine writes cannot be attributed — surface it rather
            # than returning None and letting it fail somewhere less obvious.
            raise RuntimeError(
                f"Tenant {tenant_slug!r} exists without a system actor. "
                "It was not created via provision_tenant() (ADR-011)."
            )

        human = session.scalar(
            select(User).where(
                User.tenant_id == existing.id,
                User.email == user_email,
                User.deleted_at.is_(None),
            )
        )
        if human is None:
            human = create_user(
                session,
                tenant=existing,
                actor=system_actor,
                email=user_email,
                display_name=user_display_name,
            )
            logger.info("Tenant %r existed; added missing user.", tenant_slug)
        else:
            logger.info("Tenant %r already seeded — nothing to do.", tenant_slug)

        return existing, system_actor, human

    tenant, system_actor = provision_tenant(
        session, name=tenant_name, slug=tenant_slug
    )
    human = create_user(
        session,
        tenant=tenant,
        actor=system_actor,
        email=user_email,
        display_name=user_display_name,
    )

    logger.info(
        "Seeded tenant %r with system actor %s and user %s",
        tenant_slug,
        system_actor.email,
        human.email,
    )
    return tenant, system_actor, human


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    with get_session_factory()() as session:
        tenant, system_actor, human = seed_development_data(session)
        session.commit()

        logger.info("tenant       %s  %s", tenant.id, tenant.slug)
        logger.info("system actor %s  %s", system_actor.id, system_actor.email)
        logger.info("user         %s  %s", human.id, human.email)


if __name__ == "__main__":
    main()
