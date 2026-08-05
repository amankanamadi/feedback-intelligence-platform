"""add housekeeping and amenities ratings

Revision ID: 20cba630fc82
Revises: 325affcf48e2
Create Date: 2026-08-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20cba630fc82'
down_revision: Union[str, None] = '325affcf48e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('feedback', sa.Column('housekeeping_rating', sa.Integer(), nullable=True))
    op.add_column('feedback', sa.Column('amenities_rating', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('feedback', 'amenities_rating')
    op.drop_column('feedback', 'housekeeping_rating')
