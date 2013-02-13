import os
import logging
import sqlalchemy as sa
from alembic import context

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARN)
logging.getLogger('alembic').setLevel(logging.INFO)


def run_migrations_offline():
    """ Run migrations in 'offline' mode. No engine needed. """
    url = os.environ['DATABASE']
    context.configure(url=url)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """ Run migrations in 'online' mode. Need engine and connection. """
    from content import model

    engine = sa.create_engine(os.environ['DATABASE'],
                              poolclass=sa.pool.NullPool)
    connection = engine.connect()
    context.configure(connection=connection,
                      target_metadata=model.Base.metadata)

    try:
        with context.begin_transaction():
            context.run_migrations()

    finally:
        connection.close()


if context.is_offline_mode():
    run_migrations_offline()

else:
    run_migrations_online()
