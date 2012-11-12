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
    document = relationship("Document")
    ident = sa.Column(sa.String)
    title = sa.Column(sa.String)
    text = sa.Column(sa.Text)


class ImportResult(Base):

    __tablename__ = 'import_result'
    id = sa.Column(sa.Integer, primary_key=True)
    time = sa.Column(sa.DateTime)
    document_id = sa.Column(sa.Integer, sa.ForeignKey('documents.id'))
    document = relationship("Document")
    success = sa.Column(sa.Boolean)
