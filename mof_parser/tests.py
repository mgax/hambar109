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
        summary_lines = self.lines[:50]
        self.assertIn(u"DECIZII ALE CURȚII CONSTITUȚIONALE", summary_lines)
        self.assertIn(u"SUMAR", summary_lines)
        self.assertIn(u"ORDONANȚE ȘI HOTĂRÂRI ALE GUVERNULUI ROMÂNIEI",
                      summary_lines)
        self.assertIn(u"ACTE ALE ORGANELOR DE SPECIALITATE ALE "
                      u"ADMINISTRAȚIEI PUBLICE CENTRALE", summary_lines)

        self.assertFalse(any(line.startswith(u"C U R T E A  C O N")
                             for line in self.lines))
        self.assertFalse(any(line.startswith(u"D E C I Z I I  A L E")
                             for line in self.lines))
        self.assertIn(u"DECIZIA Nr. 258", self.lines)


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
        self.assertIn((u"judiciare de timbru, precum și ale art. 29 alin. "
                       u"(6) din Legea nr. 47/1992"), cc_decision['title'])

    def test_hg_second_section_has_correct_title(self):
        hg_290 = self.data[2]
        self.assertEqual(hg_290['section'], 'hotarare-guvern')
        self.assertTrue(hg_290['title'].startswith(
                u"Hotărâre privind încetarea exercitării funcției"))
        self.assertIn((u"încetarea exercitării funcției publice de "
                       u"subprefect al județului Alba"), hg_290['title'])
        self.assertEqual(hg_290['number'], '290')

    def test_titles_end_with_no_page_number(self):
        cc_decision = self.data[0]
        self.assertTrue(cc_decision['title'].endswith(
                u"funcționarea Curții Constituționale"))

        hg_290 = self.data[2]
        self.assertTrue(hg_290['title'].endswith(u"către domnul Popa Romul"))

        bnr_act = self.data[10]
        self.assertTrue(bnr_act['title'].endswith(
                u"24 februarie\u201423 martie 2009"))

    def test_article_counts_by_section_are_correct(self):
        from collections import defaultdict
        counts = defaultdict(int)
        for article in self.data:
            counts[article['section']] += 1
        self.assertEqual(counts, {
            'decizie-cc': 1,
            'hotarare-guvern': 8,
            'act-admin-centrala': 1,
            'act-bnr': 1,
        })

    def test_cc_article_body_contains_text(self):
        cc_decision = self.data[0]
        self.assertIn(u"Pe rol se află soluționarea excepției de "
                      u"neconstituționalitate a dispozițiilor art. 2 și "
                      u"art. 20 din Legea nr. 146/1997",
                      cc_decision['body'].replace('\n', ' '))
        self.assertTrue(cc_decision['body'].startswith(u"Ioan Vida"))


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
