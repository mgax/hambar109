# encoding: utf-8
import unittest
from datetime import date
from path import path
from mof_parser import preprocess, parse, parse_tika


DATA = path(__file__).abspath().parent / 'data'


class ParserPreprocessorTest(unittest.TestCase):

    def setUp(self):
        self.raw = (DATA / 'mof1_2009_0174-tika.html').bytes()
        self.lines = preprocess(self.raw)

    def test_remove_junk(self):
        self.assertFalse(any(line.startswith('Nr. Pagina')
                             for line in self.lines))
        header = u"MONITORUL OFICIAL AL ROMÂNIEI, PARTEA I"
        self.assertFalse(any(line.startswith(header) for line in self.lines))
        self.assertFalse(any(line == '10' for line in self.lines))

    def test_headlines(self):
        self.assertIn(u"DECIZII ALE CURȚII CONSTITUȚIONALE", self.lines)
        self.assertIn(u"SUMAR", self.lines)
        self.assertIn(u"ORDONANȚE ȘI HOTĂRÂRI ALE GUVERNULUI ROMÂNIEI",
                      self.lines)
        self.assertIn(u"ACTE ALE ORGANELOR DE SPECIALITATE ALE "
                      u"ADMINISTRAȚIEI PUBLICE CENTRALE", self.lines)
        self.assertFalse(any(line.startswith(u"C U R T E A  C O N")
                             for line in self.lines))
        self.assertFalse(any(line.startswith(u"D E C I Z I I  A L E")
                             for line in self.lines))


class TikaMofParserTest(unittest.TestCase):

    def setUp(self):
        self.raw = (DATA / 'mof1_2009_0174-tika.html').bytes()
        self.lines = preprocess(self.raw)
        self.data = parse_tika(self.lines)

    def test_all_sections_found(self):
        sections = set(article['section'] for article in self.data)
        self.assertItemsEqual(sections, ['decizie-cc', 'hotarare-guvern',
                                         'act-admin-centrala', 'act-bnr'])

    def test_cc_decision_title_found(self):
        cc_decision = self.data[0]
        self.assertTrue(cc_decision['title'].startswith(
                            u"Decizia nr. 258 din 24 februarie 2009"))


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

    def test_parser_extracts_articles(self):
        out = parse(self.html)
        section_gov = out['sections'][1]
        self.assertEqual([a['title'][:62] for a in section_gov['articles']], [
            u"22. - Ordonantă de urgentă privind înfiintarea Autoritătii Nat",
            u"290. - Hotărâre privind încetarea exercitării functiei publice",
            u"291. - Hotărâre privind exercitarea, cu caracter temporar, a f",
            u"294. - Hotărâre privind modificarea raportului de serviciu al ",
            u"295. - Hotărâre privind exercitarea, cu caracter temporar, a f",
            u"296. - Hotărâre privind încetarea exercitării de către domnul ",
            u"297. - Hotărâre privind dispunerea reluării activitătii de căt",
            u"304. - Hotărâre privind exercitarea, cu caracter temporar, a f",
        ])

    def test_parser_extracts_oug_article_metadata(self):
        out = parse(self.html)
        oug_22 = out['sections'][1]['articles'][0]
        self.assertDictContainsSubset({
            'number': '22',
            'type': u"Ordonantă de urgentă",
            'summary': (u"privind înfiintarea Autoritătii Nationale pentru "
                        u"Administrare si Reglementare în Comunicatii"),
        }, oug_22)

    def test_parser_extracts_hg_article_metadata(self):
        out = parse(self.html)
        hg_290 = out['sections'][1]['articles'][1]
        self.assertDictContainsSubset({
            'number': '290',
            'type': u"Hotărâre",
            'summary': (u"privind încetarea exercitării functiei publice de "
                        u"subprefect al judetului Alba de către domnul "
                        u"Popa Romul"),
        }, hg_290)

    def test_parser_extracts_article_body(self):
        out = parse(self.html)
        body = out['sections'][1]['articles'][1]['body']
        print body
        self.assertTrue(body.startswith(
            u"Având în vedere prevederile art. 19 alin. (1) lit. a) si art."))
        self.assertIn(u"încetează exercitarea functiei publice", body)
