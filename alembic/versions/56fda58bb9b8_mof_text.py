revision = '56fda58bb9b8'
down_revision = '593416768f99'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table('mof_text',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('text', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['id'], ['mof.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('mof_text')
