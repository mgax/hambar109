from contextlib import contextmanager
import unittest
import flask


@contextmanager
def db_session(app):
    with app.app_context():
        yield flask.current_app.extensions['hambar-db'].session


class ApiTest(unittest.TestCase):

    def setUp(self):
        from content.api import api_views
        from content.model import Base, DatabaseForFlask
        self.app = flask.Flask(__name__)

        self.app.config['DATABASE'] = 'sqlite:///:memory:'
        DatabaseForFlask().initialize_app(self.app)
        with db_session(self.app) as session:
            engine = session.bind
            Base.metadata.create_all(engine)

        self.app.register_blueprint(api_views, url_prefix='/api')
        self.client = self.app.test_client()

    def test_api_returns_404_if_document_not_found(self):
        resp = self.client.get('/api/document/mof1_2007_9999')
        self.assertEqual(resp.status_code, 404)

    def test_api_returns_200_if_document_is_found(self):
        from content.model import Document
        with db_session(self.app) as session:
            session.add(Document(code='mof1_2007_0123'))

        resp = self.client.get('/api/document/mof1_2007_0123')
        self.assertEqual(resp.status_code, 200)
