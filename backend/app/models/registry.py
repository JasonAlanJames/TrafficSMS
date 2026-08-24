"""
TrafficSMS SQLAlchemy model registry.

Importing this module ensures Base.metadata contains every mapped table
required by Alembic and application startup.
"""

from app.models.entities import (
    CommunityReport,
    DuiNotice,
    EnforcementCamera,
    ReportVote,
    User,
)
from app.models.billing_event import BillingEvent
from app.models.auth_event import AuthEvent
from app.models.refresh_token import RefreshToken
from app.models.subscription import Subscription
from app.models.usage_tracking import UsageTracking
from app.models.saved_route import SavedRoute

__all__ = [
    "User",
    "AuthEvent",
    "RefreshToken",
    "Subscription",
    "UsageTracking",
    "BillingEvent",
    "CommunityReport",
    "ReportVote",
    "EnforcementCamera",
    "DuiNotice",
    "SavedRoute",
]
