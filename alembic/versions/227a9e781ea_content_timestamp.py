"""content timestamp

Revision ID: 227a9e781ea
Revises: 3351249c0c9c
Create Date: 2013-01-31 20:33:57.909582

"""

# revision identifiers, used by Alembic.
revision = '227a9e781ea'
down_revision = '3351249c0c9c'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('content', sa.Column('time', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('content', 'time')
