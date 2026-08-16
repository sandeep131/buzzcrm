"""Tenant — the isolation boundary (ADR-006, ADR-008).

Not tenant-scoped itself: it *is* the scope. See ADR-011, "Clarification to
ADR-006", for why this is the single exception to `tenant_id` everywhere.

Not Salesforce-sourced, so no `sf_id`.
"""

from sqlalchemy import Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db import Base
from src.models.base import (
    ActiveFlagMixin,
    ActorMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Tenant(
    Base,
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    ActorMixin,
    SoftDeleteMixin,
    ActiveFlagMixin,
):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        # Partial, not plain: a slug freed by a soft delete must be reusable
        # (ADR-009 constraint 2).
        Index(
            "uq_tenants_slug",
            "slug",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    def __repr__(self) -> str:
        return f"<Tenant {self.slug}>"
