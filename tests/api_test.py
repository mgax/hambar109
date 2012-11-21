import unittest
import flask
from flask import json
from util import db_session, configure_memory_db


class ApiTest(unittest.TestCase):

    def setUp(self):
        from content.api import api_views
        self.app = flask.Flask(__name__)

        configure_memory_db(self.app)

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

    def test_api_returns_act_information(self):
        from content.model import Document, Act, ActType
        with db_session(self.app) as session:
            council = ActType(code='counc', label="Revolutionary council")
            doc = Document(code='mof1_2007_0123')
            act1 = Act(document=doc, type=council,
                       ident='13', headline="Proclamation",
                       title="Independence", text="We hereby proclaim!")
            session.add_all([council, doc, act1])

        resp = self.client.get('/api/document/mof1_2007_0123')
        data = json.loads(resp.data)
        self.assertEqual(data['acts'][0]['authority'], "Revolutionary council")
        self.assertEqual(data['acts'][0]['number'], "13")
        self.assertEqual(data['acts'][0]['title'], "Independence")
        self.assertEqual(data['acts'][0]['body'], "We hereby proclaim!")
        self.assertEqual(data['acts'][0]['headline'], "Proclamation")
