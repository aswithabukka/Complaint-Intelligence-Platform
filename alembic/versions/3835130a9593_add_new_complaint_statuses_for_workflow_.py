"""Add new complaint statuses for workflow tracking

Revision ID: 3835130a9593
Revises: 001
Create Date: 2026-01-21 02:50:16.873290

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3835130a9593'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new values to complaintstatus enum
    op.execute("ALTER TYPE complaintstatus ADD VALUE IF NOT EXISTS 'pending_action'")
    op.execute("ALTER TYPE complaintstatus ADD VALUE IF NOT EXISTS 'in_progress'")
    op.execute("ALTER TYPE complaintstatus ADD VALUE IF NOT EXISTS 'resolved'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values
    # You would need to recreate the enum type to remove values
    pass
