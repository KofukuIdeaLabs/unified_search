"""deleted at column added to the form template

Revision ID: 51a029af9a37
Revises: 3fbc4ce4a8e9
Create Date: 2024-12-17 11:30:39.183366

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '51a029af9a37'
down_revision: Union[str, None] = '3fbc4ce4a8e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('form_template', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('form_template', 'deleted_at')
    # ### end Alembic commands ###
