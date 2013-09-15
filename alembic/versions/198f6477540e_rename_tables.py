revision = '198f6477540e'
down_revision = '227a9e781ea'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.rename_table('documents', 'document')
    op.rename_table('act_types', 'act_type')
    op.rename_table('acts', 'act')


def downgrade():
    op.rename_table('document', 'documents')
    op.rename_table('act_type', 'act_types')
    op.rename_table('act', 'acts')
