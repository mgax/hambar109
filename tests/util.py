from contextlib import contextmanager
import flask


@contextmanager
def db_session(app):
    with app.app_context():
        yield flask.current_app.extensions['hambar-db'].session
