"""add local SMS opt-out state

Revision ID: a4c9d7e2f531
Revises: 9a7c3e6b2d14
Create Date: 2026-08-24 14:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4c9d7e2f531"
down_revision: Union[str, Sequence[str], None] = "9a7c3e6b2d14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    if "sms_opted_out_at" not in existing_columns:
        op.add_column("users", sa.Column("sms_opted_out_at", sa.DateTime(timezone=True), nullable=True))
    if "sms_opt_out_type" not in existing_columns:
        op.add_column("users", sa.Column("sms_opt_out_type", sa.String(length=32), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    if "sms_opt_out_type" in existing_columns:
        op.drop_column("users", "sms_opt_out_type")
    if "sms_opted_out_at" in existing_columns:
        op.drop_column("users", "sms_opted_out_at")
