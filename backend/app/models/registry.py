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
from app.models.refresh_token import RefreshToken

__all__ = [
    "User",
    "RefreshToken",
    "CommunityReport",
    "ReportVote",
    "EnforcementCamera",
    "DuiNotice",
]
