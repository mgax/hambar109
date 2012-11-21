"""create Act.headline

Revision ID: 272e2fe8c8d3
Revises: 75ecb9d63cd
Create Date: 2012-11-21 21:33:55.627707

"""

# revision identifiers, used by Alembic.
revision = '272e2fe8c8d3'
down_revision = '75ecb9d63cd'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('acts', sa.Column('headline', sa.String(), nullable=True))


def downgrade():
    op.drop_column('acts', 'headline')
