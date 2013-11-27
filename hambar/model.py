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
    in_s3 = db.Column(db.Boolean)
    in_local = db.Column(db.Boolean)
    unavailable = db.Column(db.Boolean)
    errors = db.Column(db.Text)

    @property
    def pdf_filename(self):
        return (
            'mof{s.part}_{s.year}_{s.number:04d}{extension}.pdf'
            .format(s=self, extension=self.extension or '')
        )

    @property
    def local_path(self):
        base = path(flask.current_app.config['MOF_FILE_PATH'])
        return base / self.pdf_filename

    @property
    def s3_url(self):
        base = flask.current_app.config['S3_BASE_URL']
        return base + self.pdf_filename


model_manager = Manager()


@model_manager.option('alembic_args', nargs=argparse.REMAINDER)
def alembic(alembic_args):
    from alembic.config import CommandLine
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


@model_manager.command
def audit_files():
    import subprocess
    for mof in Mof.query.filter_by(year=2013):
        if mof.local_path.isfile():
            out = subprocess.check_output(['file', '-bi', mof.local_path])
            if not out.startswith('application/pdf'):
                print mof.pdf_filename
