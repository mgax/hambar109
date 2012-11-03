# encoding: utf-8
import unittest
import re
from path import path


DATA = path(__file__).abspath().parent / 'data'


tags = re.compile(r'\<[^>]+\>')
def parse(text):
    section = {}
    state = 'expect_heading'
    for line in text.splitlines():
        line = tags.sub('', line).strip()

        if state == 'expect_heading':
            if 'P A R T E A' in line:
                section['heading'] = 'PARTEA I'
                state = 'expect_title'
            continue

        if state == 'expect_title':
            if line:
                section['title'] = line
                state = 'expect_identifier'
            continue

        if state == 'expect_identifier':
            if line:
                section['identifier'] = line
                state = 'expect_content'
                break

    return [section]


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
        }, out[0])
