# encoding: utf-8
import unittest
from datetime import date
from path import path
from mof_parser import parse


DATA = path(__file__).abspath().parent / 'data'


class MofParserTest(unittest.TestCase):

    def setUp(self):
        self.text = (DATA / 'mof1_2009_0174.txt').text()

    def test_phrase_found_in_text(self):
        self.assertIn("utilizeze eficient spectrul radio", self.text)

    def test_parser_returns_one_section(self):
        out = parse(self.text)
        self.assertDictContainsSubset({
            'heading': "PARTEA I",
            'title': "LEGI, DECRETE, HOTĂRÂRI ȘI ALTE ACTE",
            'identifier': "Anul 177 (XXI) — Nr. 174 Joi, 19 martie 2009",
            'date': date(2009, 3, 19),
            'mof_number': 174,
        }, out[0])
