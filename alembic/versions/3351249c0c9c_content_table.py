"""Content table

Revision ID: 3351249c0c9c
Revises: 272e2fe8c8d3
Create Date: 2013-01-31 18:43:32.985408

"""

# revision identifiers, used by Alembic.
revision = '3351249c0c9c'
down_revision = '272e2fe8c8d3'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('content',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'))
    op.add_column(u'documents',
                  sa.Column('content_id', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column(u'documents', 'content_id')
    op.drop_table('content')
