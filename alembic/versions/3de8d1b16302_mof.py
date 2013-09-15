revision = '3de8d1b16302'
down_revision = '593355ac79cb'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.rename_table('document', 'mof')


def downgrade():
    op.rename_table('mof', 'document')
