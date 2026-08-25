"""ensure user timestamp defaults

Revision ID: c9f3a5d7e824
Revises: b8e2f4a6c713
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9f3a5d7e824"
down_revision: Union[str, Sequence[str], None] = "b8e2f4a6c713"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE users SET created_at = now() WHERE created_at IS NULL"))
    bind.execute(sa.text("UPDATE users SET updated_at = now() WHERE updated_at IS NULL"))
    op.alter_column("users", "created_at", server_default=sa.text("now()"))
    op.alter_column("users", "updated_at", server_default=sa.text("now()"))


def downgrade() -> None:
    op.alter_column("users", "updated_at", server_default=None)
    op.alter_column("users", "created_at", server_default=None)
