"""display_name column added to the indexed table

Revision ID: 651dd3732075
Revises: a8b7d881bb1e
Create Date: 2024-12-04 07:15:06.007444

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '651dd3732075'
down_revision: Union[str, None] = 'a8b7d881bb1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('indexed_table', sa.Column('display_name', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('indexed_table', 'display_name')
    # ### end Alembic commands ###
