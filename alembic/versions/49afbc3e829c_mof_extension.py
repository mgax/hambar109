revision = '49afbc3e829c'
down_revision = '2d0f61b3d65'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('mof', sa.Column('extension', sa.String(), nullable=True))


def downgrade():
    op.drop_column('mof', 'extension')
