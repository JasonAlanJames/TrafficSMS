"""add SMS compliance timestamps

Revision ID: b8e2f4a6c713
Revises: a4c9d7e2f531
Create Date: 2026-08-24 15:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8e2f4a6c713"
down_revision: Union[str, Sequence[str], None] = "a4c9d7e2f531"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    if "sms_resumed_at" not in existing_columns:
        op.add_column("users", sa.Column("sms_resumed_at", sa.DateTime(timezone=True), nullable=True))
    if "sms_last_help_at" not in existing_columns:
        op.add_column("users", sa.Column("sms_last_help_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    if "sms_last_help_at" in existing_columns:
        op.drop_column("users", "sms_last_help_at")
    if "sms_resumed_at" in existing_columns:
        op.drop_column("users", "sms_resumed_at")
