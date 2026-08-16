"""Request scope — who is asking, and which tenant they are asking within.

Every request resolves to exactly one `RequestScope`, and the repository layer
takes its tenant filter from here rather than from anything the caller passes.
That is the whole point: a request cannot widen its own scope (ADR-006).

Authentication is stubbed for MVP (ADR-007). Replacing the stub touches exactly
one function — `get_current_user()` — with no model, endpoint, or repository
change.
"""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.core.db import get_session
from src.models.tenant import Tenant
from src.models.user import User


@dataclass(frozen=True)
class RequestScope:
    """The authenticated user and their tenant.

    Frozen: nothing downstream may repoint a live request at another tenant.
    """

    user: User
    tenant: Tenant

    @property
    def tenant_id(self):
        return self.tenant.id

    @property
    def user_id(self):
        return self.user.id


class SystemActorAuthenticationError(RuntimeError):
    """Raised if authentication ever resolves to a system actor.

    ADR-011: a system actor is a pointer target, not a principal. It holds no
    privileges and must never become the authenticated user. This is raised
    rather than returned as a 401 because it means the identity layer is
    misconfigured, not that a caller supplied a bad credential.
    """


def resolve_stub_user(session: Session) -> RequestScope:
    """Resolve the seeded human user and their tenant (ADR-007 MVP stub).

    No password handling, no session management, no token validation. This is
    the single swap point: the SSO adapter validates a Buzz credential,
    resolves it to a `users` row, and returns the same `RequestScope`.
    """
    settings = get_settings()

    user = session.scalar(
        select(User).where(
            User.email == settings.auth_stub_user_email,
            User.deleted_at.is_(None),
        )
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                f"Auth stub user {settings.auth_stub_user_email!r} not found. "
                "Run `python -m src.models.seed`."
            ),
        )

    # Belt and braces. The seed never creates a system actor with this email,
    # but the check is cheap and the failure mode it guards is severe: a
    # privilege-less pointer target becoming an authenticated principal.
    # The SSO adapter must keep this guarantee (ADR-011).
    if user.is_system:
        raise SystemActorAuthenticationError(
            f"{settings.auth_stub_user_email!r} resolved to a system actor. "
            "System actors cannot authenticate (ADR-011)."
        )

    tenant = session.get(Tenant, user.tenant_id)
    if tenant is None or tenant.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User's tenant is missing or deleted.",
        )

    return RequestScope(user=user, tenant=tenant)


def get_current_user(session: Session = Depends(get_session)) -> RequestScope:
    """FastAPI dependency returning the current user **and** their tenant.

    Every route that touches data depends on this. Tenant scope flows from here
    into the repository layer and is never taken from a request parameter.
    """
    return resolve_stub_user(session)
