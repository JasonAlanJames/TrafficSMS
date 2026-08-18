from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.billing_event import BillingEvent
from app.models.entities import User
from app.models.subscription import Subscription
from app.models.usage_tracking import UsageTracking


class BillingRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_user(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_user_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_user_by_email(self, email: str) -> User | None:
        return self.db.scalar(
            select(User).where(
                func.lower(User.email) == email.strip().lower()
            )
        )

    def get_subscription_by_user_id(self, user_id: int) -> Subscription | None:
        return self.db.scalar(
            select(Subscription).where(Subscription.user_id == user_id)
        )

    def get_subscription_by_stripe_subscription_id(
        self,
        stripe_subscription_id: str,
    ) -> Subscription | None:
        return self.db.scalar(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_subscription_id
            )
        )

    def get_subscription_by_customer_id(
        self,
        stripe_customer_id: str,
    ) -> Subscription | None:
        return self.db.scalar(
            select(Subscription).where(
                Subscription.stripe_customer_id == stripe_customer_id
            )
        )

    def save_subscription(self, subscription: Subscription) -> Subscription:
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        return subscription

    def get_current_usage_record(
        self,
        user_id: int,
    ) -> UsageTracking | None:
        return self.db.scalar(
            select(UsageTracking)
            .where(UsageTracking.user_id == user_id)
            .order_by(UsageTracking.period_end.desc())
        )

    def get_usage_record_for_period(
        self,
        *,
        user_id: int,
        period_start: datetime,
    ) -> UsageTracking | None:
        return self.db.scalar(
            select(UsageTracking).where(
                UsageTracking.user_id == user_id,
                UsageTracking.period_start == period_start,
            )
        )

    def save_usage_record(self, record: UsageTracking) -> UsageTracking:
        try:
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            return record
        except IntegrityError:
            self.db.rollback()
            existing = self.get_usage_record_for_period(
                user_id=record.user_id,
                period_start=record.period_start,
            )
            if existing is not None:
                return existing
            raise

    def get_billing_events_for_user(
        self,
        user_id: int,
    ) -> list[BillingEvent]:
        return self.db.scalars(
            select(BillingEvent)
            .where(BillingEvent.user_id == user_id)
            .order_by(BillingEvent.occurred_at.desc(), BillingEvent.id.desc())
        ).all()

    def get_billing_event_by_stripe_event_id(
        self,
        stripe_event_id: str,
    ) -> BillingEvent | None:
        return self.db.scalar(
            select(BillingEvent).where(
                BillingEvent.stripe_event_id == stripe_event_id
            )
        )

    def save_billing_event(self, event: BillingEvent) -> BillingEvent:
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def record_usage_increment(
        self,
        *,
        usage_record: UsageTracking,
        count: int,
        recorded_at: datetime,
    ) -> UsageTracking | None:
        result = self.db.execute(
            update(UsageTracking)
            .where(
                UsageTracking.id == usage_record.id,
                UsageTracking.sms_used + count <= UsageTracking.sms_allowance,
            )
            .values(
                sms_used=UsageTracking.sms_used + count,
                updated_at=recorded_at,
            )
        )

        if (result.rowcount or 0) != 1:
            self.db.rollback()
            return None

        self.db.commit()
        refreshed = self.db.get(UsageTracking, usage_record.id)
        return refreshed
