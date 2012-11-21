import unittest
import flask
from util import db_session, configure_memory_db


class ImportTest(unittest.TestCase):

    def setUp(self):
        self.app = flask.Flask(__name__)
        configure_memory_db(self.app)

    def test_document_is_created_on_save(self):
        from content.mof_import import save_document_acts
        from content.model import Document

        with self.app.app_context():
            save_document_acts([], 'mof1_2007_0123')

        with db_session(self.app) as session:
            [doc] = session.query(Document).all()
            self.assertEqual(doc.code, 'mof1_2007_0123')
