from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import sqlalchemy as sa


Base = declarative_base()


class Document(Base):

    __tablename__ = 'documents'
    id = sa.Column(sa.Integer, primary_key=True)
    code = sa.Column(sa.String)
    import_time = sa.Column(sa.DateTime)


class ActType(Base):

    __tablename__ = 'act_types'
    id = sa.Column(sa.Integer, primary_key=True)
    code = sa.Column(sa.String)
    label = sa.Column(sa.String)


class Act(Base):

    __tablename__ = 'acts'
    id = sa.Column(sa.Integer, primary_key=True)
    type_id = sa.Column(sa.Integer, sa.ForeignKey('act_types.id'))
    type = relationship("ActType")
    document_id = sa.Column(sa.Integer, sa.ForeignKey('documents.id'))
    document = relationship("Document", backref='acts')
    ident = sa.Column(sa.String)
    title = sa.Column(sa.String)
    text = sa.Column(sa.Text)


class ImportResult(Base):

    __tablename__ = 'import_result'
    id = sa.Column(sa.Integer, primary_key=True)
    time = sa.Column(sa.DateTime)
    document_id = sa.Column(sa.Integer, sa.ForeignKey('documents.id'))
    document = relationship("Document", backref='import_results')
    success = sa.Column(sa.Boolean)


def get_session_maker(database=None):
    import os
    from sqlalchemy.orm import sessionmaker
    engine = sa.create_engine(database or os.environ['DATABASE'])
    return sessionmaker(bind=engine)


class DatabaseForFlask(object):

    def __init__(self):
        import flask
        self._stack = flask._app_ctx_stack

    def initialize_app(self, app):
        self.Session = get_session_maker(app.config.get('DATABASE'))
        app.extensions['hambar-db'] = self
        app.teardown_appcontext(self.teardown)

    @property
    def session(self):
        ctx = self._stack.top
        if not hasattr(ctx, 'hambar_db_session'):
            ctx.hambar_db_session = self.Session()
        return ctx.hambar_db_session

    def teardown(self, exception):
        ctx = self._stack.top
        if hasattr(ctx, 'hambar_db_session'):
            if exception is None:
                ctx.hambar_db_session.commit()
            else:
                ctx.hambar_db_session.rollback()
