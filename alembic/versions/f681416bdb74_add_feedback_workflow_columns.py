"""add feedback workflow columns

Revision ID: f681416bdb74
Revises: 66f50f104b47
Create Date: 2026-07-29 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f681416bdb74'
down_revision: Union[str, None] = '66f50f104b47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The old free-text, non-FK "user_id" string column is renamed to make
    # room for a real integer FK to users.id below. Existing values are
    # preserved for historical export/audit visibility.
    op.alter_column('feedback', 'user_id', new_column_name='submitter_user_id_legacy')

    op.add_column('feedback', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_feedback_user_id'), 'feedback', ['user_id'], unique=False)
    op.create_foreign_key(
        'fk_feedback_user_id_users', 'feedback', 'users', ['user_id'], ['id'], ondelete='SET NULL'
    )

    # op.add_column with an Enum type doesn't auto-create the Postgres type
    # the way create_table does - it must be created explicitly first (same
    # pattern as dcca72ebde4d_add_feedback_metadata_columns.py). Labels are
    # the enum members' NAMEs (NEW, IN_REVIEW, ...), not their display
    # values ("New", "In Review", ...) - SQLAlchemy's Enum binds Python
    # enum members by .name, matching every other enum column in this
    # schema (main_category_enum stores INCIDENT, not "Incident").
    feedback_status_enum = sa.Enum(
        'NEW', 'ACKNOWLEDGED', 'IN_REVIEW', 'IN_PROGRESS', 'RESOLVED', 'CLOSED', name='feedback_status_enum'
    )
    feedback_status_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'feedback',
        sa.Column('status', feedback_status_enum, nullable=False, server_default='NEW'),
    )
    op.add_column('feedback', sa.Column('internal_notes', sa.String(), nullable=True))
    op.add_column('feedback', sa.Column('admin_response', sa.String(), nullable=True))
    op.add_column('feedback', sa.Column('admin_response_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('feedback', sa.Column('acknowledgement', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('feedback', 'acknowledgement')
    op.drop_column('feedback', 'admin_response_at')
    op.drop_column('feedback', 'admin_response')
    op.drop_column('feedback', 'internal_notes')
    op.drop_column('feedback', 'status')
    op.execute("DROP TYPE feedback_status_enum")

    op.drop_constraint('fk_feedback_user_id_users', 'feedback', type_='foreignkey')
    op.drop_index(op.f('ix_feedback_user_id'), table_name='feedback')
    op.drop_column('feedback', 'user_id')

    op.alter_column('feedback', 'submitter_user_id_legacy', new_column_name='user_id')
