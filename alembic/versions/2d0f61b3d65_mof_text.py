revision = '2d0f61b3d65'
down_revision = '51fd75cec03d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('mof', sa.Column('text_json', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('mof', 'text_json')
