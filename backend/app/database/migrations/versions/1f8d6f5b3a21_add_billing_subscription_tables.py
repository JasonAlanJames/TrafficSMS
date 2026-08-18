"""add billing subscription tables

Revision ID: 1f8d6f5b3a21
Revises: c7e0a9f13b42
Create Date: 2026-08-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1f8d6f5b3a21"
down_revision: Union[str, Sequence[str], None] = "c7e0a9f13b42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def current_inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def get_index_names(
    inspector: sa.Inspector,
    table_name: str,
) -> set[str]:
    return {
        index["name"]
        for index in inspector.get_indexes(table_name)
    }


def create_subscriptions_table() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=128), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=128), nullable=True),
        sa.Column("stripe_price_id", sa.String(length=128), nullable=True),
        sa.Column("plan", sa.String(length=32), nullable=False, server_default="free"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="inactive"),
        sa.Column("sms_allowance", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("web_access_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("renewal_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_subscriptions_user_id"),
        sa.UniqueConstraint("stripe_subscription_id", name="uq_subscriptions_stripe_subscription_id"),
    )
    with op.batch_alter_table("subscriptions") as batch_op:
        batch_op.create_index("ix_subscriptions_user_id", ["user_id"], unique=True)
        batch_op.create_index("ix_subscriptions_stripe_customer_id", ["stripe_customer_id"], unique=False)
        batch_op.create_index("ix_subscriptions_stripe_subscription_id", ["stripe_subscription_id"], unique=True)
        batch_op.create_index("ix_subscriptions_stripe_price_id", ["stripe_price_id"], unique=False)
        batch_op.create_index("ix_subscriptions_plan", ["plan"], unique=False)
        batch_op.create_index("ix_subscriptions_status", ["status"], unique=False)


def create_usage_tracking_table() -> None:
    op.create_table(
        "usage_tracking",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=True),
        sa.Column("plan", sa.String(length=32), nullable=False, server_default="free"),
        sa.Column("sms_used", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("sms_allowance", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_reset_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "period_start", name="uq_usage_tracking_user_period_start"),
    )
    with op.batch_alter_table("usage_tracking") as batch_op:
        batch_op.create_index("ix_usage_tracking_user_id", ["user_id"], unique=False)
        batch_op.create_index("ix_usage_tracking_subscription_id", ["subscription_id"], unique=False)
        batch_op.create_index("ix_usage_tracking_period_start", ["period_start"], unique=False)
        batch_op.create_index("ix_usage_tracking_period_end", ["period_end"], unique=False)


def create_billing_events_table() -> None:
    op.create_table(
        "billing_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("subscription_id", sa.Integer(), nullable=True),
        sa.Column("stripe_event_id", sa.String(length=128), nullable=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="system"),
        sa.Column("amount_cents", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=16), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_event_id", name="uq_billing_events_stripe_event_id"),
    )
    with op.batch_alter_table("billing_events") as batch_op:
        batch_op.create_index("ix_billing_events_user_id", ["user_id"], unique=False)
        batch_op.create_index("ix_billing_events_subscription_id", ["subscription_id"], unique=False)
        batch_op.create_index("ix_billing_events_stripe_event_id", ["stripe_event_id"], unique=True)
        batch_op.create_index("ix_billing_events_event_type", ["event_type"], unique=False)
        batch_op.create_index("ix_billing_events_source", ["source"], unique=False)


def upgrade() -> None:
    inspector = current_inspector()

    if not table_exists(inspector, "subscriptions"):
        create_subscriptions_table()

    inspector = current_inspector()
    if not table_exists(inspector, "usage_tracking"):
        create_usage_tracking_table()

    inspector = current_inspector()
    if not table_exists(inspector, "billing_events"):
        create_billing_events_table()


def downgrade() -> None:
    inspector = current_inspector()

    if table_exists(inspector, "billing_events"):
        op.drop_table("billing_events")

    inspector = current_inspector()
    if table_exists(inspector, "usage_tracking"):
        op.drop_table("usage_tracking")

    inspector = current_inspector()
    if table_exists(inspector, "subscriptions"):
        op.drop_table("subscriptions")
