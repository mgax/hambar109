revision = '42ac4597c34'
down_revision = '2192338c340'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('mof', sa.Column('number', sa.Integer(), nullable=True))
    op.add_column('mof', sa.Column('part', sa.Integer(), nullable=True))
    op.add_column('mof', sa.Column('year', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('mof', 'year')
    op.drop_column('mof', 'part')
    op.drop_column('mof', 'number')
