"""your_descriptive_message

Revision ID: 989e39cd69b0
Revises: c6a23f5d6df5
Create Date: 2025-11-19 16:21:40.180670

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '989e39cd69b0'
down_revision: Union[str, Sequence[str], None] = 'c6a23f5d6df5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
