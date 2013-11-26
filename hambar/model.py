import argparse
import logging
import uuid
import flask
from flask.ext.script import Manager
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
from path import path

db = SQLAlchemy()


def random_uuid():
    return str(uuid.uuid4())


class Mof(db.Model):

    id = db.Column(UUID, primary_key=True, default=random_uuid)
    code = db.Column(db.String)
    year = db.Column(db.Integer)
    part = db.Column(db.Integer)
    number = db.Column(db.Integer)
    extension = db.Column(db.String)
    fetchme = db.Column(db.Boolean)
    text_json = db.Column(db.Text)

    @property
    def pdf_filename(self):
        return 'mof{s.part}_{s.year}_{s.number:04d}.pdf'.format(s=self)

    @property
    def local_path(self):
        base = path(flask.current_app.config['MOF_FILE_PATH'])
        return base / self.pdf_filename


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
