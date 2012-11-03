import unittest
from path import path


DATA = path(__file__).abspath().parent / 'data'


class MofParserTest(unittest.TestCase):

    def setUp(self):
        self.text = (DATA / 'mof1_2009_0174.txt').text()

    def test_phrase_found_in_text(self):
        self.assertIn("utilizeze eficient spectrul radio", self.text)
