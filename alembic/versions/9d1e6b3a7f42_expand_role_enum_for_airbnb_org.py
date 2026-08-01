"""expand role enum for airbnb org roles

Revision ID: 9d1e6b3a7f42
Revises: c4f7a29e18b3
Create Date: 2026-08-01 09:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d1e6b3a7f42'
down_revision: Union[str, None] = 'c4f7a29e18b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Unlike the feedback taxonomy change, existing `users` rows are real
    # accounts (logins) and are preserved, not truncated - USER becomes
    # GUEST (the equivalent submitter tier) and ADMIN becomes
    # SUPPORT_MANAGER (the equivalent staff tier) before the old enum type
    # is dropped.
    op.execute("ALTER TYPE role_enum RENAME TO role_enum_old")
    role_enum = sa.Enum(
        'GUEST', 'HOST', 'SUPPORT_MANAGER', 'OPS_MANAGER', 'PRODUCT_MANAGER', 'EXEC', name='role_enum'
    )
    role_enum.create(op.get_bind(), checkfirst=True)

    op.execute(
        "ALTER TABLE users ALTER COLUMN role DROP DEFAULT"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE role_enum USING ("
        "CASE role::text "
        "WHEN 'USER' THEN 'GUEST' "
        "WHEN 'ADMIN' THEN 'SUPPORT_MANAGER' "
        "ELSE role::text END"
        ")::role_enum"
    )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'GUEST'")
    op.execute("DROP TYPE role_enum_old")


def downgrade() -> None:
    op.execute("ALTER TYPE role_enum RENAME TO role_enum_new")
    role_enum = sa.Enum('USER', 'ADMIN', name='role_enum')
    role_enum.create(op.get_bind(), checkfirst=True)

    op.execute(
        "ALTER TABLE users ALTER COLUMN role DROP DEFAULT"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE role_enum USING ("
        "CASE role::text "
        "WHEN 'GUEST' THEN 'USER' "
        "WHEN 'HOST' THEN 'USER' "
        "ELSE 'ADMIN' END"
        ")::role_enum"
    )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'USER'")
    op.execute("DROP TYPE role_enum_new")
