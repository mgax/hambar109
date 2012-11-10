from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy as sa


Base = declarative_base()


class ActType(Base):

    __tablename__ = 'act_types'
    id = sa.Column(sa.Integer, primary_key=True)
    code = sa.Column(sa.String)
    label = sa.Column(sa.String)


class Source(Base):

    __tablename__ = 'sources'
    id = sa.Column(sa.Integer, primary_key=True)
    code = sa.Column(sa.String)


class Act(Base):

    __tablename__ = 'acts'
    id = sa.Column(sa.Integer, primary_key=True)
    type_id = sa.Column(sa.Integer, sa.ForeignKey('act_types.id'))
    source_id = sa.Column(sa.Integer, sa.ForeignKey('sources.id'))
    ident = sa.Column(sa.String)
    title = sa.Column(sa.String)
    text = sa.Column(sa.Text)
