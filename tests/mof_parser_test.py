# encoding: utf-8
import unittest
from datetime import date
from path import path
from content.mof_parser import preprocess, MofParser


DATA = path(__file__).abspath().parent / 'mof_parser_data'


def count_articles_by_section(articles):
    from collections import defaultdict
    counts = defaultdict(int)
    for article in articles:
        counts[article['section']] += 1
    return dict(counts)


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
        self.data = MofParser(self.raw).parse()

    def test_all_sections_found(self):
        sections = set(article['section'] for article in self.data)
        self.assertItemsEqual(sections, ['decizie-cc', 'hotarare-guvern',
                                         'act-admin-centrala', 'act-bnr'])

    def test_cc_decision_title_found(self):
        cc_decision = self.data[0]
        self.assertTrue(cc_decision['title'].startswith(
                            u"Decizia nr. 258 din 24 februarie 2009"))
        self.assertTrue(cc_decision['subtitle'].startswith(
                u"referitoare la excepția de neconstituționalitate"))
        self.assertTrue(cc_decision['subtitle'].endswith(
                u"și funcționarea Curții Constituționale"))
        self.assertIn((u"judiciare de timbru, precum și ale art. 29 alin. "
                       u"(6) din Legea nr. 47/1992"), cc_decision['title'])
        self.assertEqual(cc_decision['headline'],
                         u"Decizia nr. 258 din 24 februarie 2009")

    def test_hg_second_section_has_correct_title(self):
        hg_290 = self.data[2]
        self.assertEqual(hg_290['section'], 'hotarare-guvern')
        self.assertTrue(hg_290['title'].startswith(
                u"Hotărâre privind încetarea exercitării funcției"))
        self.assertIn((u"încetarea exercitării funcției publice de "
                       u"subprefect al județului Alba"), hg_290['title'])
        self.assertEqual(hg_290['number'], '290')
        self.assertEqual(hg_290['headline'], u"Hotărâre")

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
        counts = count_articles_by_section(self.data)
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
        #self.assertTrue(cc_decision['body'].startswith(u"Ioan Vida"))

    def test_last_article_contains_text(self):
        bnr_act = self.data[10]
        self.assertIn(u"ratele dobânzilor plătite la rezervele minime",
                      bnr_act['body'])


class MofParserTest_2010_0666(unittest.TestCase):

    def setUp(self):
        self.raw = (DATA / 'mof1_2010_0666.html').bytes()
        self.data = MofParser(self.raw).parse()

    def test_article_count(self):
        counts = count_articles_by_section(self.data)
        self.assertEqual(counts, {
            'decret-presedinte': 10,
            'hotarare-guvern': 1,
            'act-admin-centrala': 12,
        })
