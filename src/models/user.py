"""User — audit actor for everything (ADR-007).

Authentication is stubbed for MVP; this table is real from migration one so
that audit entries can carry a database-enforced actor FK.

Not Salesforce-sourced, so no `sf_id`.
"""

from sqlalchemy import Boolean, Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db import Base
from src.models.base import (
    ActiveFlagMixin,
    ActorMixin,
    SoftDeleteMixin,
    TenantScopedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class User(
    Base,
    UUIDPrimaryKeyMixin,
    TenantScopedMixin,
    TimestampMixin,
    ActorMixin,
    SoftDeleteMixin,
    ActiveFlagMixin,
):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)

    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    """Marks the tenant's system actor (ADR-011).

    A system actor holds no privileges and cannot authenticate — it exists to
    be pointed at as `created_by` for writes no human made (bootstrap, import
    batches, later AI proposals). `get_current_user()` must never return it,
    and the SSO adapter must refuse to resolve any credential to it.

    It is excluded from user *listings*, not from resolution by ID: rendering
    an audit entry must still produce "Imported by System". That exclusion is a
    third query invariant and belongs in the issue #3 repository base, not in
    individual endpoints.
    """

    __table_args__ = (
        # Email is unique per tenant, not globally — two tenants may legitimately
        # hold the same person (ADR-006 constraint 3 applies the same logic to
        # sf_id). Partial so a soft delete frees the address (ADR-009).
        Index(
            "uq_users_tenant_email",
            "tenant_id",
            "email",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        # Exactly one system actor per tenant, enforced by the database rather
        # than left to a code review to catch (ADR-011 constraint 3).
        Index(
            "uq_users_one_system_actor_per_tenant",
            "tenant_id",
            unique=True,
            postgresql_where=text("is_system AND deleted_at IS NULL"),
        ),
    )

    def __repr__(self) -> str:
        kind = "system" if self.is_system else "user"
        return f"<User {self.email} ({kind})>"
