"""Add catchup and distribution strategies to Goal model

Revision ID: cb8a12a85b44
Revises: 
Create Date: 2025-06-16 18:27:24.881500

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb8a12a85b44'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('goals', schema=None) as batch_op:
        batch_op.add_column(sa.Column('task_distribution_strategy', sa.String(), nullable=False, server_default='all'))
        batch_op.add_column(sa.Column('catchup_strategy', sa.String(), nullable=False, server_default='all'))



def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('goals', schema=None) as batch_op:
        batch_op.drop_column('catchup_strategy')
        batch_op.drop_column('task_distribution_strategy')
