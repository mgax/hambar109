import argparse
from flask.ext.script import Manager
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import sqlalchemy as sa

model_manager = Manager()
db = SQLAlchemy()


class Content(db.Model):

    __tablename__ = 'content'
    id = sa.Column(sa.Integer, primary_key=True)
    time = sa.Column(sa.DateTime, default=sa.func.now())
    text = sa.Column(sa.Text)


class Document(db.Model):

    __tablename__ = 'documents'
    id = sa.Column(sa.Integer, primary_key=True)
    code = sa.Column(sa.String)
    import_time = sa.Column(sa.DateTime)
    content_id = sa.Column(sa.Integer, sa.ForeignKey('content.id'))
    content = relationship('Content')


class ActType(db.Model):

    __tablename__ = 'act_types'
    id = sa.Column(sa.Integer, primary_key=True)
    code = sa.Column(sa.String)
    label = sa.Column(sa.String)


class Act(db.Model):

    __tablename__ = 'acts'
    id = sa.Column(sa.Integer, primary_key=True)
    type_id = sa.Column(sa.Integer, sa.ForeignKey('act_types.id'))
    type = relationship("ActType")
    document_id = sa.Column(sa.Integer, sa.ForeignKey('documents.id'))
    document = relationship("Document", backref='acts')
    ident = sa.Column(sa.String)
    title = sa.Column(sa.String)
    text = sa.Column(sa.Text)
    headline = sa.Column(sa.String)


class ImportResult(db.Model):

    __tablename__ = 'import_result'
    id = sa.Column(sa.Integer, primary_key=True)
    time = sa.Column(sa.DateTime, default=sa.func.now())
    document_id = sa.Column(sa.Integer, sa.ForeignKey('documents.id'))
    document = relationship("Document", backref='import_results')
    success = sa.Column(sa.Boolean)


@model_manager.option('alembic_args', nargs=argparse.REMAINDER)
def alembic(alembic_args):
    from alembic.config import CommandLine
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
