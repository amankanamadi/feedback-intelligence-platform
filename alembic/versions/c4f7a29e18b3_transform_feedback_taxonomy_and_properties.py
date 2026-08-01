"""transform feedback taxonomy and add properties table

Revision ID: c4f7a29e18b3
Revises: b79829587e0a
Create Date: 2026-08-01 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4f7a29e18b3'
down_revision: Union[str, None] = 'b79829587e0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This app is dev-only - every existing `feedback` row is itself
    # synthetic SaaS-domain demo data being replaced wholesale by the
    # Airbnb-domain reseed that follows this migration, so it's safe to
    # empty the table (and its dependents, via CASCADE) rather than write a
    # value-mapping data migration for the enum changes below.
    op.execute("TRUNCATE TABLE feedback CASCADE")

    op.drop_column('feedback', 'main_category')
    op.drop_column('feedback', 'sub_category')
    op.drop_column('feedback', 'source')
    op.drop_column('feedback', 'product')
    op.drop_column('feedback', 'module')
    op.drop_column('feedback', 'region')

    op.execute("DROP TYPE main_category_enum")
    op.execute("DROP TYPE sub_category_enum")
    op.execute("DROP TYPE feedback_source_enum")

    main_category_enum = sa.Enum(
        'GUEST_REVIEW', 'HOST_COMPLAINT', 'SUPPORT_TICKET', name='main_category_enum'
    )
    main_category_enum.create(op.get_bind(), checkfirst=True)

    sub_category_enum = sa.Enum(
        'CLEANLINESS', 'WIFI', 'CHECK_IN', 'AMENITIES', 'HOST_COMMUNICATION',
        'SAFETY', 'MAINTENANCE',
        'BOOKING_EXPERIENCE', 'PAYMENTS', 'REFUNDS', 'APP_ISSUES', 'FEATURE_REQUESTS',
        name='sub_category_enum',
    )
    sub_category_enum.create(op.get_bind(), checkfirst=True)

    feedback_source_enum = sa.Enum(
        'MOBILE_APP', 'WEBSITE', 'POST_STAY_SURVEY', 'HOST_DASHBOARD', 'EMAIL',
        'SUPPORT_CHAT', 'API', 'QR_CODE',
        name='feedback_source_enum',
    )
    feedback_source_enum.create(op.get_bind(), checkfirst=True)

    op.add_column('feedback', sa.Column('main_category', main_category_enum, nullable=True))
    op.add_column('feedback', sa.Column('sub_category', sub_category_enum, nullable=True))
    op.add_column('feedback', sa.Column('source', feedback_source_enum, nullable=True))
    op.add_column('feedback', sa.Column('recommended_action', sa.String(), nullable=True))

    # Unlike op.add_column above, op.create_table auto-creates any Enum
    # type used by its columns - an explicit .create() call here would
    # collide with that and raise DuplicateObject.
    property_type_enum = sa.Enum(
        'ENTIRE_HOME', 'PRIVATE_ROOM', 'SHARED_ROOM', name='property_type_enum'
    )

    op.create_table(
        'properties',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('host_name', sa.String(), nullable=False),
        sa.Column('city', sa.String(), nullable=False),
        sa.Column('country', sa.String(), nullable=False),
        sa.Column('property_type', property_type_enum, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_properties_city'), 'properties', ['city'], unique=False)

    op.add_column('feedback', sa.Column('property_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_feedback_property_id'), 'feedback', ['property_id'], unique=False)
    op.create_foreign_key(
        'fk_feedback_property_id_properties', 'feedback', 'properties', ['property_id'], ['id'], ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_feedback_property_id_properties', 'feedback', type_='foreignkey')
    op.drop_index(op.f('ix_feedback_property_id'), table_name='feedback')
    op.drop_column('feedback', 'property_id')

    op.drop_index(op.f('ix_properties_city'), table_name='properties')
    op.drop_table('properties')
    op.execute("DROP TYPE property_type_enum")

    op.drop_column('feedback', 'recommended_action')
    op.drop_column('feedback', 'source')
    op.drop_column('feedback', 'sub_category')
    op.drop_column('feedback', 'main_category')

    op.execute("DROP TYPE feedback_source_enum")
    op.execute("DROP TYPE sub_category_enum")
    op.execute("DROP TYPE main_category_enum")

    main_category_enum = sa.Enum('INCIDENT', 'SERVICE_REQUEST', 'GENERAL_FEEDBACK', name='main_category_enum')
    main_category_enum.create(op.get_bind(), checkfirst=True)
    sub_category_enum = sa.Enum(
        'PRODUCT_BUG', 'APPLICATION_CRASH', 'LOGIN_ISSUE', 'PAYMENT_FAILURE', 'PERFORMANCE_ISSUE',
        'SECURITY_ISSUE', 'DATA_LOSS', 'INTEGRATION_FAILURE', 'FEATURE_REQUEST', 'UI_UX_IMPROVEMENT',
        'DOCUMENTATION_REQUEST', 'API_ENHANCEMENT', 'ACCESSIBILITY_IMPROVEMENT', 'NEW_INTEGRATION',
        'APPRECIATION', 'COMPLAINT', 'PRICING_FEEDBACK', 'CUSTOMER_SUPPORT', 'QUESTION', 'SUGGESTION',
        name='sub_category_enum',
    )
    sub_category_enum.create(op.get_bind(), checkfirst=True)
    feedback_source_enum = sa.Enum(
        'WEB_FORM', 'IN_APP_WIDGET', 'MOBILE_APP', 'EMAIL', 'API', 'SURVEY', 'CHATBOT', 'QR_CODE',
        name='feedback_source_enum',
    )
    feedback_source_enum.create(op.get_bind(), checkfirst=True)

    op.add_column('feedback', sa.Column('main_category', main_category_enum, nullable=True))
    op.add_column('feedback', sa.Column('sub_category', sub_category_enum, nullable=True))
    op.add_column('feedback', sa.Column('source', feedback_source_enum, nullable=True))
    op.add_column('feedback', sa.Column('product', sa.String(), nullable=True))
    op.add_column('feedback', sa.Column('module', sa.String(), nullable=True))
    op.add_column('feedback', sa.Column('region', sa.String(), nullable=True))
