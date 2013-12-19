revision = '462252e38047'
down_revision = '31bbdca4f17'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('mof', sa.Column('es_add', sa.Boolean(), nullable=True))
    op.execute("UPDATE mof SET es_add = false")
    op.alter_column('mof', 'es_add', nullable=True)


def downgrade():
    op.drop_column('mof', 'es_add')
