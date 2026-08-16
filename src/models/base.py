"""Shared column mixins for domain tables.

The field list is fixed by DOMAIN_MODEL.md ("Base Fields — Every Domain
Table"). Mixins exist so that a table declares which blocks apply to it rather
than restating nine columns per model — issue #5 onward compose these.

Actor foreign keys are DEFERRABLE INITIALLY DEFERRED. `tenants.created_by`
points at `users` while `users.tenant_id` points back at `tenants`, which is
circular at row level: neither row can be inserted first under immediate
constraint checking. Deferring to COMMIT lets a tenant and its system actor be
written in one transaction (ADR-011 constraint 2). `use_alter` tells SQLAlchemy
to emit these as ALTER statements after both tables exist, which is what breaks
the same cycle at DDL level.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Uuid, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

# NOTE: `sf_id` is a base field in DOMAIN_MODEL.md but has no mixin here.
# Nothing in issue #2 is Salesforce-sourced, and the partial unique index it
# needs — (tenant_id, sf_id) WHERE deleted_at IS NULL AND sf_id IS NOT NULL,
# per ADR-009 constraint 2 — is per-table anyway. Issue #5 adds both alongside
# Company, where they can actually be exercised.


def _actor_fk(column_name: str) -> ForeignKey:
    """A deferrable FK to users.id.

    A fresh ForeignKey per column — the object binds to the table it is
    attached to and cannot be shared between models.

    RESTRICT: users are soft-deleted (ADR-009), so a physical delete that would
    orphan an audit actor is a bug. Refuse it at the database rather than
    cascading and silently destroying attribution.
    """
    return ForeignKey(
        "users.id",
        name=column_name,
        deferrable=True,
        initially="DEFERRED",
        use_alter=True,
        ondelete="RESTRICT",
    )


class UUIDPrimaryKeyMixin:
    """UUID primary key, generated application-side.

    Client-side generation is load-bearing, not a style choice: the system
    actor is inserted with `created_by` set to its own id, which requires the
    id to be known before the INSERT (ADR-011 constraint 1).
    """

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    """created_at / updated_at, both timezone-aware.

    Defaults are server-side so rows written outside the ORM (migrations,
    imports, manual SQL) still get correct timestamps.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ActorMixin:
    """Who created and last updated the row.

    NOT NULL by ADR-011 — every row has a real actor, because every tenant is
    seeded with a system actor for writes no human made. There is deliberately
    no NULL case for downstream audit reads to handle.
    """

    @declared_attr
    def created_by(cls) -> Mapped[uuid.UUID]:  # noqa: N805
        return mapped_column(
            Uuid, _actor_fk(f"fk_{cls.__tablename__}_created_by"), nullable=False
        )

    @declared_attr
    def updated_by(cls) -> Mapped[uuid.UUID]:  # noqa: N805
        return mapped_column(
            Uuid, _actor_fk(f"fk_{cls.__tablename__}_updated_by"), nullable=False
        )


class SoftDeleteMixin:
    """Soft delete per ADR-009. Records are never physically removed.

    `deleted_by` is nullable because it is only set when a delete happens —
    unlike created_by/updated_by, which are total.

    The `deleted_at IS NULL` read predicate belongs in the issue #3 repository
    base, never in individual queries (ADR-009 constraint 1).
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    @declared_attr
    def deleted_by(cls) -> Mapped[uuid.UUID | None]:  # noqa: N805
        return mapped_column(
            Uuid, _actor_fk(f"fk_{cls.__tablename__}_deleted_by"), nullable=True
        )


class TenantScopedMixin:
    """tenant_id — NOT NULL and indexed on every domain table (ADR-006).

    `tenants` is the one table that does not carry this, because it *is* the
    scope (ADR-011, "Clarification to ADR-006"). Every other table, including
    `users`, obeys the rule without exception.
    """

    @declared_attr
    def tenant_id(cls) -> Mapped[uuid.UUID]:  # noqa: N805
        return mapped_column(
            Uuid,
            ForeignKey(
                "tenants.id",
                name=f"fk_{cls.__tablename__}_tenant_id",
                deferrable=True,
                initially="DEFERRED",
                ondelete="RESTRICT",
            ),
            nullable=False,
            index=True,
        )


class ActiveFlagMixin:
    """is_active — soft enable/disable, distinct from soft delete.

    Deactivating is reversible and routine; deleting is not.
    """

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
