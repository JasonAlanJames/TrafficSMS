"""consolidate primary schema and auth

Revision ID: c7e0a9f13b42
Revises: 768bae8c0f8b
Create Date: 2026-08-17 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c7e0a9f13b42"
down_revision: Union[str, Sequence[str], None] = "768bae8c0f8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


AUTH_USER_COLUMNS: list[tuple[str, sa.Column]] = [
    ("password_hash", sa.Column("password_hash", sa.String(length=255), nullable=True)),
    (
        "email_verified",
        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    ),
    ("verification_token", sa.Column("verification_token", sa.String(length=64), nullable=True)),
    (
        "verification_token_expires_at",
        sa.Column(
            "verification_token_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    ),
    (
        "phone_verified",
        sa.Column(
            "phone_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    ),
    ("password_reset_token", sa.Column("password_reset_token", sa.String(length=64), nullable=True)),
    (
        "password_reset_expires_at",
        sa.Column(
            "password_reset_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    ),
    (
        "is_active",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    ),
    (
        "is_locked",
        sa.Column(
            "is_locked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    ),
    (
        "failed_login_attempts",
        sa.Column(
            "failed_login_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    ),
    ("last_login", sa.Column("last_login", sa.DateTime(timezone=True), nullable=True)),
    (
        "last_failed_login",
        sa.Column("last_failed_login", sa.DateTime(timezone=True), nullable=True),
    ),
    (
        "password_changed_at",
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
    ),
    ("sms_consent_at", sa.Column("sms_consent_at", sa.DateTime(timezone=True), nullable=True)),
    (
        "marketing_consent_at",
        sa.Column("marketing_consent_at", sa.DateTime(timezone=True), nullable=True),
    ),
    (
        "updated_at",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    ),
]

AUTH_USER_INDEXES: list[tuple[str, list[str], bool]] = [
    ("ix_users_email_verified", ["email_verified"], False),
    ("ix_users_verification_token", ["verification_token"], True),
    ("ix_users_password_reset_token", ["password_reset_token"], True),
    ("ix_users_is_active", ["is_active"], False),
    ("ix_users_is_locked", ["is_locked"], False),
]

REFRESH_TOKEN_INDEXES: list[tuple[str, list[str], bool]] = [
    ("ix_refresh_tokens_user_id", ["user_id"], False),
    ("ix_refresh_tokens_token_hash", ["token_hash"], True),
    ("ix_refresh_tokens_expires_at", ["expires_at"], False),
    ("ix_refresh_tokens_revoked", ["revoked"], False),
]

REFRESH_TOKEN_FOREIGN_KEYS: list[tuple[str, list[str], str, list[str], str | None]] = [
    (
        "fk_refresh_tokens_user_id_users",
        ["user_id"],
        "users",
        ["id"],
        "CASCADE",
    ),
    (
        "fk_refresh_tokens_replaced_by_token_id_refresh_tokens",
        ["replaced_by_token_id"],
        "refresh_tokens",
        ["id"],
        "SET NULL",
    ),
]


def current_inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def get_column_names(
    inspector: sa.Inspector,
    table_name: str,
) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def has_index(
    inspector: sa.Inspector,
    table_name: str,
    index_name: str,
    columns: list[str],
    unique: bool,
) -> bool:
    target_columns = tuple(columns)
    for index in inspector.get_indexes(table_name):
        existing_columns = tuple(index.get("column_names") or [])
        if index.get("name") == index_name:
            return True
        if existing_columns == target_columns and bool(index.get("unique")) == unique:
            return True
    return False


def has_matching_foreign_key(
    inspector: sa.Inspector,
    table_name: str,
    constrained_columns: list[str],
    referred_table: str,
    referred_columns: list[str],
) -> bool:
    target_columns = tuple(constrained_columns)
    target_referred_columns = tuple(referred_columns)

    for foreign_key in inspector.get_foreign_keys(table_name):
        existing_columns = tuple(foreign_key.get("constrained_columns") or [])
        existing_referred_columns = tuple(foreign_key.get("referred_columns") or [])
        if (
            existing_columns == target_columns
            and foreign_key.get("referred_table") == referred_table
            and existing_referred_columns == target_referred_columns
        ):
            return True

    return False


def create_users_table() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("phone_e164", sa.String(length=32), nullable=True),
        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("verification_token", sa.String(length=64), nullable=True),
        sa.Column(
            "verification_token_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "phone_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("password_reset_token", sa.String(length=64), nullable=True),
        sa.Column(
            "password_reset_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "is_locked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "failed_login_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failed_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sms_consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("marketing_consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("home_location", sa.String(length=255), nullable=True),
        sa.Column("work_location", sa.String(length=255), nullable=True),
        sa.Column("gym_location", sa.String(length=255), nullable=True),
        sa.Column("school_location", sa.String(length=255), nullable=True),
        sa.Column("default_state", sa.String(length=2), nullable=True),
        sa.Column(
            "default_country",
            sa.String(length=2),
            nullable=False,
            server_default="US",
        ),
        sa.Column(
            "subscription_status",
            sa.String(length=32),
            nullable=False,
            server_default="inactive",
        ),
        sa.Column("subscription_plan", sa.String(length=32), nullable=True),
        sa.Column("stripe_customer_id", sa.String(length=128), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=128), nullable=True),
        sa.Column("stripe_price_id", sa.String(length=128), nullable=True),
        sa.Column("current_period_start", sa.DateTime(), nullable=True),
        sa.Column("current_period_end", sa.DateTime(), nullable=True),
        sa.Column(
            "cancel_at_period_end",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("last_payment_date", sa.DateTime(), nullable=True),
        sa.Column("next_billing_date", sa.DateTime(), nullable=True),
        sa.Column("subscription_updated_at", sa.DateTime(), nullable=True),
        sa.Column(
            "monthly_sms_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("phone_e164", name="uq_users_phone_e164"),
        sa.UniqueConstraint("verification_token", name="uq_users_verification_token"),
        sa.UniqueConstraint("password_reset_token", name="uq_users_password_reset_token"),
        sa.UniqueConstraint("stripe_customer_id", name="uq_users_stripe_customer_id"),
        sa.UniqueConstraint(
            "stripe_subscription_id",
            name="uq_users_stripe_subscription_id",
        ),
    )
    with op.batch_alter_table("users") as batch_op:
        batch_op.create_index("ix_users_email", ["email"], unique=True)
        batch_op.create_index("ix_users_phone_e164", ["phone_e164"], unique=True)
        batch_op.create_index("ix_users_email_verified", ["email_verified"], unique=False)
        batch_op.create_index(
            "ix_users_verification_token",
            ["verification_token"],
            unique=True,
        )
        batch_op.create_index(
            "ix_users_password_reset_token",
            ["password_reset_token"],
            unique=True,
        )
        batch_op.create_index("ix_users_is_active", ["is_active"], unique=False)
        batch_op.create_index("ix_users_is_locked", ["is_locked"], unique=False)
        batch_op.create_index(
            "ix_users_subscription_status",
            ["subscription_status"],
            unique=False,
        )
        batch_op.create_index(
            "ix_users_subscription_plan",
            ["subscription_plan"],
            unique=False,
        )
        batch_op.create_index(
            "ix_users_stripe_customer_id",
            ["stripe_customer_id"],
            unique=True,
        )
        batch_op.create_index(
            "ix_users_stripe_subscription_id",
            ["stripe_subscription_id"],
            unique=True,
        )
        batch_op.create_index("ix_users_stripe_price_id", ["stripe_price_id"], unique=False)


def ensure_users_columns(inspector: sa.Inspector) -> None:
    existing_columns = get_column_names(inspector, "users")

    with op.batch_alter_table("users") as batch_op:
        for column_name, column in AUTH_USER_COLUMNS:
            if column_name not in existing_columns:
                batch_op.add_column(column)


def ensure_users_indexes(inspector: sa.Inspector) -> None:
    existing_columns = get_column_names(inspector, "users")

    with op.batch_alter_table("users") as batch_op:
        for index_name, columns, unique in AUTH_USER_INDEXES:
            if not set(columns).issubset(existing_columns):
                continue
            if not has_index(inspector, "users", index_name, columns, unique):
                batch_op.create_index(index_name, columns, unique=unique)


def create_refresh_tokens_table() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_token_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("device_name", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_refresh_tokens_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["replaced_by_token_id"],
            ["refresh_tokens.id"],
            name="fk_refresh_tokens_replaced_by_token_id_refresh_tokens",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_tokens"),
    )


def ensure_refresh_token_foreign_keys(inspector: sa.Inspector) -> None:
    existing_columns = get_column_names(inspector, "refresh_tokens")

    for constraint_name, columns, referred_table, referred_columns, ondelete in REFRESH_TOKEN_FOREIGN_KEYS:
        if not set(columns).issubset(existing_columns):
            continue
        if has_matching_foreign_key(
            inspector,
            "refresh_tokens",
            columns,
            referred_table,
            referred_columns,
        ):
            continue
        op.create_foreign_key(
            constraint_name,
            "refresh_tokens",
            referred_table,
            columns,
            referred_columns,
            ondelete=ondelete,
        )


def ensure_refresh_token_indexes(inspector: sa.Inspector) -> None:
    existing_columns = get_column_names(inspector, "refresh_tokens")

    with op.batch_alter_table("refresh_tokens") as batch_op:
        for index_name, columns, unique in REFRESH_TOKEN_INDEXES:
            if not set(columns).issubset(existing_columns):
                continue
            if not has_index(inspector, "refresh_tokens", index_name, columns, unique):
                batch_op.create_index(index_name, columns, unique=unique)


def upgrade() -> None:
    inspector = current_inspector()
    if not table_exists(inspector, "users"):
        create_users_table()
    else:
        ensure_users_columns(inspector)

    inspector = current_inspector()
    ensure_users_indexes(inspector)

    if not table_exists(inspector, "refresh_tokens"):
        create_refresh_tokens_table()

    inspector = current_inspector()
    ensure_refresh_token_foreign_keys(inspector)
    inspector = current_inspector()
    ensure_refresh_token_indexes(inspector)


def downgrade() -> None:
    inspector = current_inspector()

    if table_exists(inspector, "refresh_tokens"):
        op.drop_table("refresh_tokens")

    inspector = current_inspector()
    if not table_exists(inspector, "users"):
        return

    existing_columns = get_column_names(inspector, "users")
    removable_columns = [column_name for column_name, _ in AUTH_USER_COLUMNS]

    with op.batch_alter_table("users") as batch_op:
        for column_name in removable_columns:
            if column_name in existing_columns:
                batch_op.drop_column(column_name)
