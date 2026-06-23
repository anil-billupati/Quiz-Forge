"""Model registry.

Importing this package registers every model on ``Base.metadata`` so that
SQLAlchemy can always resolve cross-model foreign keys (e.g. user.tenant_id →
organization.id), regardless of which entry point imported first. Any new model
module must be added here.
"""
from app.models.base import Base
from app.models.organization import Organization, TenantSettings
from app.models.user import RefreshToken, User
from app.models.tenant_usage import TenantUsageRecord
from app.models.contest import Contest, ContestLifecycleEvent
from app.models.foundation_probe import FoundationProbe

__all__ = [
    "Base",
    "Organization",
    "TenantSettings",
    "User",
    "RefreshToken",
    "TenantUsageRecord",
    "Contest",
    "ContestLifecycleEvent",
    "FoundationProbe",
]
