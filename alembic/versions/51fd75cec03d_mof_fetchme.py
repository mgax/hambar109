revision = '51fd75cec03d'
down_revision = '42ac4597c34'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('mof', sa.Column('fetchme', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column('mof', 'fetchme')
