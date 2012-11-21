from contextlib import contextmanager
import flask


@contextmanager
def db_session(app):
    with app.app_context():
        yield flask.current_app.extensions['hambar-db'].session



def configure_memory_db(app):
    from content.model import Base, DatabaseForFlask
    app.config['DATABASE'] = 'sqlite:///:memory:'
    DatabaseForFlask().initialize_app(app)
    with db_session(app) as session:
        engine = session.bind
        Base.metadata.create_all(engine)
