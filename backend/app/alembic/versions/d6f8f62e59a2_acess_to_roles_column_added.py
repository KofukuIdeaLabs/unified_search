"""acess_to_roles column added

Revision ID: d6f8f62e59a2
Revises: fa5b374dbc71
Create Date: 2024-12-05 07:05:40.087091

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd6f8f62e59a2'
down_revision: Union[str, None] = 'fa5b374dbc71'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('indexed_table', sa.Column('access_to_roles', postgresql.ARRAY(sa.UUID()), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('indexed_table', 'access_to_roles')
   
    # ### end Alembic commands ###