# encoding: utf-8
import unittest
from datetime import date
from path import path
from mof_parser import parse


DATA = path(__file__).abspath().parent / 'data'


class MofParserTest(unittest.TestCase):

    def setUp(self):
        self.html = (DATA / 'mof1_2009_0174.html').text('windows-1252')

    def test_phrase_found_in_text(self):
        self.assertIn("utilizeze eficient spectrul radio", self.html)

    def test_parser_returns_section_meta(self):
        out = parse(self.html)
        self.assertDictContainsSubset({
            'heading': "PARTEA I",
            'title': u"LEGI, DECRETE, HOTĂRÂRI SI ALTE ACTE",
            'date': date(2009, 3, 19),
            'mof_number': 174,
        }, out['meta'])

    def test_parser_extracts_main_sections(self):
        out = parse(self.html)
        self.assertEqual(len(out['sections']), 4)
        self.assertEqual([s['title'] for s in out['sections']], [
            u"DECIZII ALE CURTII CONSTITUTIONALE",
            u"ORDONANTE SI HOTĂRÂRI ALE GUVERNULUI ROMÂNIEI",
            (u"ACTE ALE ORGANELOR DE SPECIALITATE ALE "
                 u"ADMINISTRATIEI PUBLICE CENTRALE"),
            u"ACTE ALE BĂNCII NATIONALE A ROMÂNIEI",
        ])
