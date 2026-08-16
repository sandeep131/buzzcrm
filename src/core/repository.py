"""Repository base — where the query invariants actually live.

Three predicates are applied here, on every read, so that no endpoint has to
remember them (ADR-006 c.2, ADR-009 c.1, ADR-011):

1. `tenant_id = <current tenant>`     always, no bypass exists
2. `deleted_at IS NULL`               bypass: include_deleted=True
3. `is_system = false`                bypass: include_system=True
                                      listing only, never single-row resolution

**There is deliberately no way to query across tenants.** No keyword argument
expresses it, so ADR-006 c.5 ("no cross-tenant joins, ever") is enforced by the
shape of this API rather than by reviewer discipline. Widening tenant scope
requires editing this file, which is a conspicuous diff.

The bypasses that do exist are named keyword arguments so every one of them is
greppable:

    grep -rnE "include_deleted|include_system" src/

Sync sessions throughout (ADR-010).
"""

from datetime import datetime, timezone
from typing import Any, Generic, Sequence, TypeVar
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from src.core.db import Base
from src.core.scope import RequestScope
from src.models.user import User

ModelT = TypeVar("ModelT", bound=Base)

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

# Fields the repository owns outright. A caller may pass them; they are
# discarded and replaced from the request scope. Tenant and authorship come
# from who is asking, never from the payload.
SCOPE_CONTROLLED_FIELDS = frozenset(
    {"tenant_id", "created_by", "updated_by", "deleted_at", "deleted_by"}
)

# Additionally immutable once set. `deleted_at` is absent deliberately:
# restoring a soft-deleted row is a real operation, but it needs its own
# method rather than arriving as an incidental field update.
IMMUTABLE_FIELDS = frozenset({"id", "tenant_id", "created_by", "created_at"})


class TenantScopedRepository(Generic[ModelT]):
    """Base class for every tenant-scoped domain model.

    Subclasses set `model`. `tenants` itself is not managed here — it has no
    `tenant_id` because it *is* the scope (ADR-011, Clarification to ADR-006).
    """

    model: type[ModelT]

    def __init__(self, session: Session, scope: RequestScope) -> None:
        if not hasattr(self.model, "tenant_id"):
            # A model without tenant_id cannot be scoped, so it must not be
            # reachable through this class at all. Failing loudly at
            # construction beats silently returning unscoped rows.
            raise TypeError(
                f"{self.model.__name__} has no tenant_id and cannot be managed "
                "by TenantScopedRepository."
            )

        self.session = session
        self.scope = scope

    # --- query construction ------------------------------------------------

    @property
    def _supports_system_flag(self) -> bool:
        return hasattr(self.model, "is_system")

    def _scoped_select(
        self,
        *,
        include_deleted: bool = False,
        include_system: bool = False,
    ) -> Select:
        """The only place a SELECT for this model is built.

        Every read path goes through here, so an invariant added here is added
        everywhere at once.
        """
        statement = select(self.model).where(
            self.model.tenant_id == self.scope.tenant_id
        )

        if not include_deleted:
            statement = statement.where(self.model.deleted_at.is_(None))

        if self._supports_system_flag and not include_system:
            statement = statement.where(self.model.is_system.is_(False))

        return statement

    # --- reads -------------------------------------------------------------

    def list(
        self,
        *,
        include_deleted: bool = False,
        include_system: bool = False,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> Sequence[ModelT]:
        limit = max(1, min(limit, MAX_PAGE_SIZE))
        offset = max(0, offset)

        statement = (
            self._scoped_select(
                include_deleted=include_deleted, include_system=include_system
            )
            .order_by(self.model.created_at, self.model.id)
            .limit(limit)
            .offset(offset)
        )
        return self.session.scalars(statement).all()

    def get(
        self,
        entity_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> ModelT | None:
        """Fetch one row by id, or None.

        None rather than a cross-tenant error: a row in another tenant must be
        indistinguishable from a row that does not exist, or the response
        itself leaks which ids are real.

        Note there is no `include_system` here. Invariant 3 applies to
        *listing*, not to resolution — an audit entry's actor must always
        resolve so the UI can render "Imported by System" (ADR-011).
        """
        statement = self._scoped_select(
            include_deleted=include_deleted, include_system=True
        ).where(self.model.id == entity_id)

        return self.session.scalar(statement)

    def count(
        self,
        *,
        include_deleted: bool = False,
        include_system: bool = False,
    ) -> int:
        """Counted in the database — never by materialising rows."""
        inner = self._scoped_select(
            include_deleted=include_deleted, include_system=include_system
        ).subquery()

        return self.session.scalar(select(func.count()).select_from(inner)) or 0

    # --- writes ------------------------------------------------------------

    def create(self, **values: Any) -> ModelT:
        """Create a row inside the current tenant, attributed to the current user.

        `tenant_id`, `created_by`, and `updated_by` are taken from the scope and
        overwrite anything the caller passed. A caller cannot plant a row in
        another tenant or forge authorship, even by accident.

        Lifecycle fields are stripped too — a create must not be able to write
        a row that is born soft-deleted.

        Not stripped: `is_system`. It is a User-specific field, guarded by the
        one-per-tenant partial unique index (ADR-011 c.3) and by the explicit
        Pydantic field lists that #7 puts in front of this layer. Worth knowing
        it is reachable from a raw `create()` call.

        Audit entries for this write arrive in #4, hooked at this layer so no
        endpoint has to remember them.
        """
        for field in SCOPE_CONTROLLED_FIELDS:
            values.pop(field, None)

        entity = self.model(
            tenant_id=self.scope.tenant_id,
            created_by=self.scope.user_id,
            updated_by=self.scope.user_id,
            **values,
        )
        self.session.add(entity)
        self.session.flush()
        return entity

    def update(self, entity_id: UUID, **values: Any) -> ModelT | None:
        """Update a row in the current tenant. Returns None if not visible.

        Going through `get()` is what makes cross-tenant and soft-deleted rows
        un-updatable — the same predicate that hides them on read.
        """
        entity = self.get(entity_id)
        if entity is None:
            return None

        for field in IMMUTABLE_FIELDS | {"deleted_at", "deleted_by"}:
            values.pop(field, None)

        for key, value in values.items():
            setattr(entity, key, value)

        entity.updated_by = self.scope.user_id
        self.session.flush()
        return entity

    def soft_delete(self, entity_id: UUID) -> ModelT | None:
        """Soft-delete a row (ADR-009). Returns None if not visible.

        The row stays present so its audit entries keep resolving. Re-deleting
        an already-deleted row is a no-op returning None, because `get()` will
        not find it.
        """
        entity = self.get(entity_id)
        if entity is None:
            return None

        entity.deleted_at = datetime.now(timezone.utc)
        entity.deleted_by = self.scope.user_id
        entity.updated_by = self.scope.user_id
        self.session.flush()
        return entity


class UserRepository(TenantScopedRepository[User]):
    """Users, scoped to the current tenant.

    Listing excludes system actors by default; `get()` still resolves them so
    audit attribution renders (ADR-011).
    """

    model = User
