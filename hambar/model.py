import argparse
import logging
import uuid
from flask.ext.script import Manager
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID

db = SQLAlchemy()


def random_uuid():
    return str(uuid.uuid4())


class Mof(db.Model):

    id = db.Column(UUID, primary_key=True, default=random_uuid)
    code = db.Column(db.String)
    year = db.Column(db.Integer)
    part = db.Column(db.Integer)
    number = db.Column(db.Integer)
    fetchme = db.Column(db.Boolean)
    text_json = db.Column(db.Text)


model_manager = Manager()


@model_manager.option('alembic_args', nargs=argparse.REMAINDER)
def alembic(alembic_args):
    from alembic.config import CommandLine
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    logging.getLogger('alembic').setLevel(logging.INFO)
    CommandLine().main(argv=alembic_args)


@model_manager.command
def sync():
    db.create_all()
    alembic(['stamp', 'head'])


@model_manager.command
def revision(message=None):
    if message is None:
        message = raw_input('revision name: ')
    return alembic(['revision', '--autogenerate', '-m', message])


@model_manager.command
def upgrade(revision='head'):
    return alembic(['upgrade', revision])


@model_manager.command
def downgrade(revision):
    return alembic(['downgrade', revision])
