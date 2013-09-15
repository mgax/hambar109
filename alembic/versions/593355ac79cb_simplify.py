revision = '593355ac79cb'
down_revision = '198f6477540e'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.drop_table(u'act')
    op.drop_table(u'content')
    op.drop_table(u'import_result')
    op.drop_table(u'act_type')
    op.drop_column('document', u'content_id')
    op.drop_column('document', u'import_time')


def downgrade():
    raise NotImplementedError
