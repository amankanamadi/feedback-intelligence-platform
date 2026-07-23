"""add pgvector embedding column

Revision ID: 21be712d245b
Revises: 68ab49907f0a
Create Date: 2026-07-23 11:50:47.724151

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '21be712d245b'
down_revision: Union[str, None] = '68ab49907f0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column("feedback", sa.Column("embedding", Vector(1536), nullable=True))
    op.create_index(
        "ix_feedback_embedding_hnsw_cosine",
        "feedback",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_feedback_embedding_hnsw_cosine", table_name="feedback")
    op.drop_column("feedback", "embedding")
    # Deliberately not dropping the `vector` extension - other objects may
    # depend on it, and DROP EXTENSION would fail; leave that to a manual step.
