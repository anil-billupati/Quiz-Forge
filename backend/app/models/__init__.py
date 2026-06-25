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
from app.models.group import Group
from app.models.foundation_probe import FoundationProbe
from app.models.configuration_block import ConfigurationBlock
from app.models.wildcard_config import WildcardConfig
from app.models.elimination import Checkpoint, EliminationRule
from app.models.question import Option, Question
from app.models.registration import Registration
from app.models.execution import ContestExecutionState, QuestionWindow

__all__ = [
    "Base",
    "Organization",
    "TenantSettings",
    "User",
    "RefreshToken",
    "TenantUsageRecord",
    "Contest",
    "ContestLifecycleEvent",
    "Group",
    "FoundationProbe",
    "ConfigurationBlock",
    "WildcardConfig",
    "EliminationRule",
    "Checkpoint",
    "Question",
    "Option",
    "Registration",
    "ContestExecutionState",
    "QuestionWindow",
]
