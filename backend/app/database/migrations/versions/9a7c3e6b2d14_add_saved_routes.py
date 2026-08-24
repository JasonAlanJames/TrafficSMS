"""add custom saved routes

Revision ID: 9a7c3e6b2d14
Revises: 5d6b7c8e9f10
Create Date: 2026-08-24 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a7c3e6b2d14"
down_revision: Union[str, Sequence[str], None] = "5d6b7c8e9f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "saved_routes" in inspector.get_table_names():
        return

    op.create_table(
        "saved_routes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("normalized_name", sa.String(length=80), nullable=False),
        sa.Column("origin_text", sa.String(length=255), nullable=False),
        sa.Column("destination_text", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sms_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("web_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "normalized_name", name="uq_saved_routes_user_alias"),
    )
    op.create_index("ix_saved_routes_user_id", "saved_routes", ["user_id"], unique=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "saved_routes" not in inspector.get_table_names():
        return
    op.drop_index("ix_saved_routes_user_id", table_name="saved_routes")
    op.drop_table("saved_routes")
