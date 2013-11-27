revision = '593416768f99'
down_revision = '19a098034a12'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('mof', sa.Column('s3_name', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('mof', 's3_name')
