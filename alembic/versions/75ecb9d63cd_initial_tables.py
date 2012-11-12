"""initial tables

Revision ID: 75ecb9d63cd
Revises: None
Create Date: 2012-11-12 23:18:22.031888

"""

# revision identifiers, used by Alembic.
revision = '75ecb9d63cd'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('documents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(), nullable=True),
    sa.Column('import_time', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('act_types',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(), nullable=True),
    sa.Column('label', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('import_result',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=True),
    sa.Column('document_id', sa.Integer(), nullable=True),
    sa.Column('success', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('acts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('type_id', sa.Integer(), nullable=True),
    sa.Column('document_id', sa.Integer(), nullable=True),
    sa.Column('ident', sa.String(), nullable=True),
    sa.Column('title', sa.String(), nullable=True),
    sa.Column('text', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
    sa.ForeignKeyConstraint(['type_id'], ['act_types.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('acts')
    op.drop_table('import_result')
    op.drop_table('act_types')
    op.drop_table('documents')
