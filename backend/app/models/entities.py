from __future__ import annotations
from datetime import datetime
from enum import Enum
from sqlalchemy import String, DateTime, Integer, Float, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class SubscriptionStatus(str, Enum):
    inactive = "inactive"
    active = "active"
    past_due = "past_due"
    canceled = "canceled"

class SubscriptionPlan(str, Enum):
    standard = "standard"
    unlimited = "unlimited"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        index=True,
    )

    phone_e164: Mapped[str | None] = mapped_column(
        String(32),
        unique=True,
        index=True,
    )

    home_area: Mapped[str | None] = mapped_column(
        String(120)
    )

    #
    # Subscription Information
    #

    subscription_status: Mapped[str] = mapped_column(
        String(32),
        default=SubscriptionStatus.inactive.value,
        index=True,
    )

    subscription_plan: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        index=True,
    )

    #
    # Stripe
    #

    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(128),
        unique=True,
        index=True,
    )

    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(128),
        unique=True,
        index=True,
    )

    stripe_price_id: Mapped[str | None] = mapped_column(
        String(128),
        index=True,
    )

    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime
    )

    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime
    )

    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    last_payment_date: Mapped[datetime | None] = mapped_column(
        DateTime
    )

    next_billing_date: Mapped[datetime | None] = mapped_column(
        DateTime
    )

    subscription_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime
    )

    #
    # Usage
    #

    monthly_sms_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    #
    # Audit
    #

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )


class CommunityReport(Base):
    __tablename__ = "community_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    report_type: Mapped[str] = mapped_column(String(64), index=True)
    road_name: Mapped[str] = mapped_column(String(160), index=True)
    direction: Mapped[str | None] = mapped_column(String(16))
    area_label: Mapped[str] = mapped_column(String(160))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), default="recently_reported")
    still_there_votes: Mapped[int] = mapped_column(Integer, default=0)
    cleared_votes: Mapped[int] = mapped_column(Integer, default=0)
    unsure_votes: Mapped[int] = mapped_column(Integer, default=0)
    reported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class ReportVote(Base):
    __tablename__ = "report_votes"
    __table_args__ = (UniqueConstraint("report_id", "voter_key", name="uq_report_voter"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("community_reports.id"), index=True)
    voter_key: Mapped[str] = mapped_column(String(128))
    vote: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EnforcementCamera(Base):
    __tablename__ = "enforcement_cameras"
    id: Mapped[int] = mapped_column(primary_key=True)
    camera_type: Mapped[str] = mapped_column(String(64))
    road_name: Mapped[str] = mapped_column(String(160), index=True)
    area_label: Mapped[str] = mapped_column(String(160))
    direction: Mapped[str | None] = mapped_column(String(16))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    source_type: Mapped[str] = mapped_column(String(32))
    source_url: Mapped[str | None] = mapped_column(String(500))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class DuiNotice(Base):
    __tablename__ = "dui_notices"
    id: Mapped[int] = mapped_column(primary_key=True)
    agency: Mapped[str] = mapped_column(String(200))
    area_label: Mapped[str] = mapped_column(String(200), index=True)
    notice_text: Mapped[str] = mapped_column(String(1000))
    source_url: Mapped[str] = mapped_column(String(500))
    starts_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime)
