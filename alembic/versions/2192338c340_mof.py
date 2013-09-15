revision = '2192338c340'
down_revision = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table('mof',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('code', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('mof')
