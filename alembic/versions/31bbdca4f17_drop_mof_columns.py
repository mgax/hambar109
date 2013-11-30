revision = '31bbdca4f17'
down_revision = '56fda58bb9b8'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_column('mof', u'in_s3')
    op.drop_column('mof', u'text_json')


def downgrade():
    op.add_column('mof', sa.Column(u'text_json', sa.TEXT(), nullable=True))
    op.add_column('mof', sa.Column(u'in_s3', sa.BOOLEAN(), nullable=True))
