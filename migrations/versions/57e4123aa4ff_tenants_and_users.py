"""tenants and users

Revision ID: 57e4123aa4ff
Revises:
Create Date: 2026-08-16 15:02:02.361032

Every migration MUST have a working downgrade (AGENTS.md rule 4).

Hand-adjusted from autogenerate. `tenants.created_by` references `users` while
`users.tenant_id` references `tenants`, so neither table can be created with all
its foreign keys inline — autogenerate emitted them inside both CREATE TABLEs,
which fails on the first one. The tables are created bare here and the actor
foreign keys added afterwards, with the downgrade dropping them before the
tables so the cycle unwinds in the right order.

The actor FKs are DEFERRABLE INITIALLY DEFERRED so a tenant and its system actor
can be inserted in one transaction (ADR-011 constraint 2). Re-running
autogenerate will reproduce the broken inline form — adjust it the same way.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "57e4123aa4ff"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (constraint_name, source_table, source_column)
ACTOR_FOREIGN_KEYS = [
    ("fk_tenants_created_by", "tenants", "created_by"),
    ("fk_tenants_updated_by", "tenants", "updated_by"),
    ("fk_tenants_deleted_by", "tenants", "deleted_by"),
    ("fk_users_created_by", "users", "created_by"),
    ("fk_users_updated_by", "users", "updated_by"),
    ("fk_users_deleted_by", "users", "deleted_by"),
]


def upgrade() -> None:
    # --- tenants -----------------------------------------------------------
    # No tenant_id: tenants IS the scope (ADR-011, Clarification to ADR-006).
    # No sf_id: not sourced from Salesforce.
    op.create_table(
        "tenants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tenants_deleted_at"), "tenants", ["deleted_at"])
    # Partial: a slug freed by a soft delete must be reusable (ADR-009).
    op.create_index(
        "uq_tenants_slug",
        "tenants",
        ["slug"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # --- users -------------------------------------------------------------
    # tenant_id can be inline: tenants exists by now.
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("is_system", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_users_tenant_id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_deleted_at"), "users", ["deleted_at"])
    op.create_index(op.f("ix_users_tenant_id"), "users", ["tenant_id"])
    # Email is unique per tenant, not globally (same logic as ADR-006 c.3).
    op.create_index(
        "uq_users_tenant_email",
        "users",
        ["tenant_id", "email"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    # Exactly one system actor per tenant, enforced by the database rather than
    # left to a code review to catch (ADR-011 constraint 3).
    op.create_index(
        "uq_users_one_system_actor_per_tenant",
        "users",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("is_system AND deleted_at IS NULL"),
    )

    # --- actor foreign keys ------------------------------------------------
    # Added last: both tables must exist before either can reference the other.
    for name, table, column in ACTOR_FOREIGN_KEYS:
        op.create_foreign_key(
            name,
            table,
            "users",
            [column],
            ["id"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        )


def downgrade() -> None:
    # Constraints first — dropping users while tenants still references it
    # fails, which is the mirror of the create-order problem above.
    for name, table, _column in ACTOR_FOREIGN_KEYS:
        op.drop_constraint(name, table, type_="foreignkey")

    op.drop_index("uq_users_one_system_actor_per_tenant", table_name="users")
    op.drop_index("uq_users_tenant_email", table_name="users")
    op.drop_index(op.f("ix_users_tenant_id"), table_name="users")
    op.drop_index(op.f("ix_users_deleted_at"), table_name="users")
    op.drop_table("users")

    op.drop_index("uq_tenants_slug", table_name="tenants")
    op.drop_index(op.f("ix_tenants_deleted_at"), table_name="tenants")
    op.drop_table("tenants")
