"""SQLAlchemy models.

Importing this package registers every model on `Base.metadata`. Alembic's
env.py imports it so autogenerate sees the full schema — a model that is not
reachable from here is invisible to migrations.
"""

from src.models.tenant import Tenant
from src.models.user import User

__all__ = ["Tenant", "User"]
