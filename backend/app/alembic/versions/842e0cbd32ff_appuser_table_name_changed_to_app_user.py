"""appuser table name changed to app_user

Revision ID: 842e0cbd32ff
Revises: d6f8f62e59a2
Create Date: 2024-12-16 05:34:56.724817

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '842e0cbd32ff'
down_revision: Union[str, None] = 'd6f8f62e59a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('app_user',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('full_name', sa.String(length=255), nullable=True),
    sa.Column('email', sa.String(length=100), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.Column('role_id', sa.UUID(), nullable=True),
    sa.Column('org_id', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['org_id'], ['organization.id'], ),
    sa.ForeignKeyConstraint(['role_id'], ['role.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_app_user_email'), 'app_user', ['email'], unique=True)
    op.create_index(op.f('ix_app_user_full_name'), 'app_user', ['full_name'], unique=False)
    op.create_index(op.f('ix_app_user_id'), 'app_user', ['id'], unique=False)
    op.drop_index('ix_appuser_email', table_name='appuser')
    op.drop_index('ix_appuser_full_name', table_name='appuser')
    op.drop_index('ix_appuser_id', table_name='appuser')

    op.drop_constraint('search_user_id_fkey', 'search', type_='foreignkey')
    op.drop_table('appuser')
    op.create_foreign_key(None, 'search', 'app_user', ['user_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'search', type_='foreignkey')
    op.create_foreign_key('search_user_id_fkey', 'search', 'appuser', ['user_id'], ['id'])
    op.create_table('appuser',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('full_name', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
    sa.Column('email', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.Column('hashed_password', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('is_active', sa.BOOLEAN(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('deleted_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('role_id', sa.UUID(), autoincrement=False, nullable=True),
    sa.Column('org_id', sa.UUID(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['org_id'], ['organization.id'], name='appuser_org_id_fkey'),
    sa.ForeignKeyConstraint(['role_id'], ['role.id'], name='appuser_role_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='appuser_pkey')
    )
    op.create_index('ix_appuser_id', 'appuser', ['id'], unique=False)
    op.create_index('ix_appuser_full_name', 'appuser', ['full_name'], unique=False)
    op.create_index('ix_appuser_email', 'appuser', ['email'], unique=True)
    op.drop_index(op.f('ix_app_user_id'), table_name='app_user')
    op.drop_index(op.f('ix_app_user_full_name'), table_name='app_user')
    op.drop_index(op.f('ix_app_user_email'), table_name='app_user')
    op.drop_table('app_user')
    # ### end Alembic commands ###