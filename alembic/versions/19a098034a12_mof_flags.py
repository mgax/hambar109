revision = '19a098034a12'
down_revision = '49afbc3e829c'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('mof', sa.Column('in_s3', sa.Boolean(), nullable=True))
    op.add_column('mof', sa.Column('in_local', sa.Boolean(), nullable=True))
    op.add_column('mof', sa.Column('unavailable', sa.Boolean(), nullable=True))
    op.add_column('mof', sa.Column('errors', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('mof', 'errors')
    op.drop_column('mof', 'unavailable')
    op.drop_column('mof', 'in_local')
    op.drop_column('mof', 'in_s3')
