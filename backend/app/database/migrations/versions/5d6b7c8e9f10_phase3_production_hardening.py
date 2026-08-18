"""phase 3 production hardening

Revision ID: 5d6b7c8e9f10
Revises: 1f8d6f5b3a21
Create Date: 2026-08-17 14:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "5d6b7c8e9f10"
down_revision: Union[str, Sequence[str], None] = "1f8d6f5b3a21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


USER_HARDENING_COLUMNS: list[tuple[str, sa.Column]] = [
    (
        "verification_sent_at",
        sa.Column("verification_sent_at", sa.DateTime(timezone=True), nullable=True),
    ),
    (
        "password_reset_requested_at",
        sa.Column(
            "password_reset_requested_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    ),
    ("locked_until", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True)),
    (
        "session_token_version",
        sa.Column(
            "session_token_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    ),
    ("pending_email", sa.Column("pending_email", sa.String(length=320), nullable=True)),
    (
        "pending_email_verification_token",
        sa.Column(
            "pending_email_verification_token",
            sa.String(length=64),
            nullable=True,
        ),
    ),
    (
        "pending_email_verification_expires_at",
        sa.Column(
            "pending_email_verification_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    ),
    (
        "phone_verification_requested_at",
        sa.Column(
            "phone_verification_requested_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    ),
]

AUTH_EVENTS_INDEXES: list[tuple[str, list[str], bool]] = [
    ("ix_auth_events_user_id", ["user_id"], False),
    ("ix_auth_events_identifier", ["identifier"], False),
    ("ix_auth_events_event_type", ["event_type"], False),
    ("ix_auth_events_outcome", ["outcome"], False),
    ("ix_auth_events_ip_address", ["ip_address"], False),
    ("ix_auth_events_occurred_at", ["occurred_at"], False),
]

USER_TIMESTAMP_COLUMNS: list[tuple[str, bool]] = [
    ("current_period_start", True),
    ("current_period_end", True),
    ("last_payment_date", True),
    ("next_billing_date", True),
    ("subscription_updated_at", True),
    ("created_at", False),
]


def current_inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def get_column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def get_column(inspector: sa.Inspector, table_name: str, column_name: str) -> dict | None:
    for column in inspector.get_columns(table_name):
        if column["name"] == column_name:
            return column
    return None


def has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(
        index.get("name") == index_name
        for index in inspector.get_indexes(table_name)
    )


def has_unique_constraint(
    inspector: sa.Inspector,
    table_name: str,
    columns: list[str],
) -> bool:
    target_columns = tuple(columns)
    for constraint in inspector.get_unique_constraints(table_name):
        if tuple(constraint.get("column_names") or []) == target_columns:
            return True
    return False


def create_auth_events_table() -> None:
    op.create_table(
        "auth_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("identifier", sa.String(length=320), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("event_data", sa.JSON(), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def ensure_auth_events_indexes(inspector: sa.Inspector) -> None:
    existing_columns = get_column_names(inspector, "auth_events")

    with op.batch_alter_table("auth_events") as batch_op:
        for index_name, columns, unique in AUTH_EVENTS_INDEXES:
            if not set(columns).issubset(existing_columns):
                continue
            if not has_index(inspector, "auth_events", index_name):
                batch_op.create_index(index_name, columns, unique=unique)


def ensure_user_hardening_columns(inspector: sa.Inspector) -> None:
    existing_columns = get_column_names(inspector, "users")

    with op.batch_alter_table("users") as batch_op:
        for column_name, column in USER_HARDENING_COLUMNS:
            if column_name not in existing_columns:
                batch_op.add_column(column)

        if not has_unique_constraint(inspector, "users", ["pending_email"]):
            batch_op.create_unique_constraint(
                "uq_users_pending_email",
                ["pending_email"],
            )

        if not has_unique_constraint(
            inspector,
            "users",
            ["pending_email_verification_token"],
        ):
            batch_op.create_unique_constraint(
                "uq_users_pending_email_verification_token",
                ["pending_email_verification_token"],
            )


def ensure_refresh_token_hardening_columns(inspector: sa.Inspector) -> None:
    existing_columns = get_column_names(inspector, "refresh_tokens")
    if "last_used_at" in existing_columns:
        return

    with op.batch_alter_table("refresh_tokens") as batch_op:
        batch_op.add_column(
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True)
        )


def ensure_subscription_hardening_columns(inspector: sa.Inspector) -> None:
    existing_columns = get_column_names(inspector, "subscriptions")

    with op.batch_alter_table("subscriptions") as batch_op:
        if "grace_period_end" not in existing_columns:
            batch_op.add_column(
                sa.Column("grace_period_end", sa.DateTime(timezone=True), nullable=True)
            )
        if "trial_end" not in existing_columns:
            batch_op.add_column(
                sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True)
            )
        if "last_reconciled_at" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "last_reconciled_at",
                    sa.DateTime(timezone=True),
                    nullable=True,
                )
            )

        batch_op.alter_column(
            "web_access_enabled",
            existing_type=sa.Boolean(),
            server_default=sa.text("false"),
            existing_nullable=False,
        )


def alter_user_timestamp_columns(to_timezone: bool) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    inspector = current_inspector()
    if not table_exists(inspector, "users"):
        return

    for column_name, nullable in USER_TIMESTAMP_COLUMNS:
        column = get_column(inspector, "users", column_name)
        if column is None:
            continue

        current_type = column.get("type")
        current_timezone = bool(getattr(current_type, "timezone", False))

        if current_timezone == to_timezone:
            continue

        op.alter_column(
            "users",
            column_name,
            existing_type=sa.DateTime(timezone=current_timezone),
            type_=sa.DateTime(timezone=to_timezone),
            existing_nullable=nullable,
            postgresql_using=f"{column_name} AT TIME ZONE 'UTC'",
        )


def drop_duplicate_unique_index_if_safe(
    inspector: sa.Inspector,
    *,
    table_name: str,
    index_name: str,
    columns: list[str],
) -> None:
    if not has_index(inspector, table_name, index_name):
        return

    if not has_unique_constraint(inspector, table_name, columns):
        return

    with op.batch_alter_table(table_name) as batch_op:
        batch_op.drop_index(index_name)


def drop_duplicate_unique_indexes() -> None:
    inspector = current_inspector()

    duplicates = [
        ("users", "ix_users_email", ["email"]),
        ("users", "ix_users_phone_e164", ["phone_e164"]),
        ("users", "ix_users_verification_token", ["verification_token"]),
        ("users", "ix_users_password_reset_token", ["password_reset_token"]),
        ("users", "ix_users_stripe_customer_id", ["stripe_customer_id"]),
        ("users", "ix_users_stripe_subscription_id", ["stripe_subscription_id"]),
        ("subscriptions", "ix_subscriptions_user_id", ["user_id"]),
        (
            "subscriptions",
            "ix_subscriptions_stripe_subscription_id",
            ["stripe_subscription_id"],
        ),
        ("billing_events", "ix_billing_events_stripe_event_id", ["stripe_event_id"]),
    ]

    for table_name, index_name, columns in duplicates:
        if not table_exists(inspector, table_name):
            continue
        drop_duplicate_unique_index_if_safe(
            inspector,
            table_name=table_name,
            index_name=index_name,
            columns=columns,
        )
        inspector = current_inspector()


def recreate_duplicate_unique_indexes() -> None:
    inspector = current_inspector()

    definitions = [
        ("users", "ix_users_email", ["email"]),
        ("users", "ix_users_phone_e164", ["phone_e164"]),
        ("users", "ix_users_verification_token", ["verification_token"]),
        ("users", "ix_users_password_reset_token", ["password_reset_token"]),
        ("users", "ix_users_stripe_customer_id", ["stripe_customer_id"]),
        ("users", "ix_users_stripe_subscription_id", ["stripe_subscription_id"]),
        ("subscriptions", "ix_subscriptions_user_id", ["user_id"]),
        (
            "subscriptions",
            "ix_subscriptions_stripe_subscription_id",
            ["stripe_subscription_id"],
        ),
        ("billing_events", "ix_billing_events_stripe_event_id", ["stripe_event_id"]),
    ]

    for table_name, index_name, columns in definitions:
        if not table_exists(inspector, table_name):
            continue
        if has_index(inspector, table_name, index_name):
            continue
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.create_index(index_name, columns, unique=True)
        inspector = current_inspector()


def upgrade() -> None:
    inspector = current_inspector()

    if table_exists(inspector, "users"):
        ensure_user_hardening_columns(inspector)

    inspector = current_inspector()
    if table_exists(inspector, "refresh_tokens"):
        ensure_refresh_token_hardening_columns(inspector)

    inspector = current_inspector()
    if table_exists(inspector, "subscriptions"):
        ensure_subscription_hardening_columns(inspector)

    inspector = current_inspector()
    if not table_exists(inspector, "auth_events"):
        create_auth_events_table()

    inspector = current_inspector()
    if table_exists(inspector, "auth_events"):
        ensure_auth_events_indexes(inspector)

    alter_user_timestamp_columns(to_timezone=True)
    drop_duplicate_unique_indexes()


def downgrade() -> None:
    inspector = current_inspector()

    recreate_duplicate_unique_indexes()
    alter_user_timestamp_columns(to_timezone=False)

    inspector = current_inspector()
    if table_exists(inspector, "auth_events"):
        op.drop_table("auth_events")

    inspector = current_inspector()
    if table_exists(inspector, "subscriptions"):
        with op.batch_alter_table("subscriptions") as batch_op:
            existing_columns = get_column_names(inspector, "subscriptions")
            if "last_reconciled_at" in existing_columns:
                batch_op.drop_column("last_reconciled_at")
            if "trial_end" in existing_columns:
                batch_op.drop_column("trial_end")
            if "grace_period_end" in existing_columns:
                batch_op.drop_column("grace_period_end")
            batch_op.alter_column(
                "web_access_enabled",
                existing_type=sa.Boolean(),
                server_default=sa.text("true"),
                existing_nullable=False,
            )

    inspector = current_inspector()
    if table_exists(inspector, "refresh_tokens"):
        existing_columns = get_column_names(inspector, "refresh_tokens")
        if "last_used_at" in existing_columns:
            with op.batch_alter_table("refresh_tokens") as batch_op:
                batch_op.drop_column("last_used_at")

    inspector = current_inspector()
    if table_exists(inspector, "users"):
        existing_columns = get_column_names(inspector, "users")
        with op.batch_alter_table("users") as batch_op:
            if has_unique_constraint(inspector, "users", ["pending_email_verification_token"]):
                batch_op.drop_constraint(
                    "uq_users_pending_email_verification_token",
                    type_="unique",
                )
            if has_unique_constraint(inspector, "users", ["pending_email"]):
                batch_op.drop_constraint(
                    "uq_users_pending_email",
                    type_="unique",
                )

            removable_columns = [
                "phone_verification_requested_at",
                "pending_email_verification_expires_at",
                "pending_email_verification_token",
                "pending_email",
                "session_token_version",
                "locked_until",
                "password_reset_requested_at",
                "verification_sent_at",
            ]
            for column_name in removable_columns:
                if column_name in existing_columns:
                    batch_op.drop_column(column_name)
