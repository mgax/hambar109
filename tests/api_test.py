import unittest
import flask


class ApiTest(unittest.TestCase):

    def setUp(self):
        self.app = flask.Flask(__name__)

    def test_api_returns_404_if_document_not_found(self):
        client = self.app.test_client()
        resp = client.get('/api/document/mof1_2007_9999')
        self.assertEqual(resp.status_code, 404)
