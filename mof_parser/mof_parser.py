# encoding: utf-8
import re
from datetime import date
import logging
import lxml.html, lxml.cssselect


log = logging.getLogger(__name__)


MONTH = {
    'martie': 3,
}


HEADLINES = [
    u"DECIZII ALE CURTII CONSTITUTIONALE",
    u"ORDONANTE SI HOTĂRÂRI ALE GUVERNULUI ROMÂNIEI",
    u"ACTE ALE ORGANELOR DE SPECIALITATE ALE ADMINISTRATIEI PUBLICE CENTRALE",
    u"ACTE ALE BĂNCII NATIONALE A ROMÂNIEI",
]


ARTICLE_TYPES = [

    {'type': 'decizie-cc',
     'group-headline': u"DECIZII ALE CURȚII CONSTITUȚIONALE"},

    {'type': 'hotarare-guvern',
     'group-headline': u"ORDONANȚE ȘI HOTĂRÂRI ALE GUVERNULUI ROMÂNIEI"},

    {'type': 'act-admin-centrala',
     'group-headline': (u"ACTE ALE ORGANELOR DE SPECIALITATE ALE "
                        u"ADMINISTRAȚIEI PUBLICE CENTRALE")},

    {'type': 'act-bnr',
     'group-headline': u"ACTE ALE BĂNCII NAȚIONALE A ROMÂNIEI"},

]

ARTICLE_TYPE = {t['type']: t for t in ARTICLE_TYPES}

ARTICLE_TYPE_BY_HEADLINE = {t['group-headline']: t for t in ARTICLE_TYPES}


HEADLINES2 = [t['group-headline'] for t in ARTICLE_TYPES]

AUTHORITIES = [
    u"CURTEA CONSTITUTIONALĂ",
    u"GUVERNUL ROMÂNIEI",
    u"MINISTERUL FINANTELOR PUBLICE",
    u"BANCA NATIONALĂ A ROMÂNIEI",
]


class HtmlElementList(list):

    def text(self):
        return ' '.join(e.text_content() for e in self)


class HtmlPage(object):

    def __init__(self, html):
        self._doc = lxml.html.fromstring(html)

    def select(self, css_selector):
        sel = lxml.cssselect.CSSSelector(css_selector)
        return HtmlElementList(sel(self._doc))


spaced_headline = re.compile(r'^(\w\s{1,2})+\w$', re.UNICODE)
spaced_headline_space = re.compile(r'\s{1,2}')


def preprocess(html):
    lines = []
    page = HtmlPage(html)
    for el in page.select('body > div > *'):
        text = el.text_content().strip()
        wordtext = cleanspace(text)
        lines.append(wordtext)

    header = None

    lineno = -1
    while lineno < len(lines) - 1:
        lineno += 1
        line = lines[lineno]

        if not line:
            continue

        if line == 'Nr. Pagina Nr. Pagina':
            lines[lineno:lineno+1] = []

        if header is None:
            if line.startswith(u"MONITORUL OFICIAL AL ROMÂNIEI, PARTEA"):
                header = line
                log.debug('(%d) Identified header %r', lineno, header)

        if line == header:
            log.debug('(%d) Remove repeating header', lineno)
            lines[lineno:lineno+1] = []
            next_line = lines[lineno]
            if all(ch in '0123456789' for ch in next_line):
                log.debug('(%d) Also remove page number after header %r',
                          lineno, next_line)
                lines[lineno:lineno+1] = []
            continue

        if spaced_headline.match(line) is not None:
            replace = lambda m: m.group(0)[1:]
            fixed_line = spaced_headline_space.sub(replace, line)
            log.debug('(%d) Fix spaced headline %r -> %r',
                      lineno, line, fixed_line)
            lines[lineno] = fixed_line
            continue

        for headline in HEADLINES2:
            if line == headline:
                log.debug('(%d) Found headline %r', lineno, line)
                continue
            elif headline.startswith(line):
                log.debug('(%d) Found start of headline %r', lineno, line)
                for n in range(2, 10):
                    concat = ' '.join(lines[lineno:lineno+n])
                    log.debug('Trying %d lines: %r', n, concat)
                    if concat == headline:
                        log.debug("It's a match!")
                        lines[lineno:lineno+n] = [concat]
                        break

    return lines


class CcParser(object):

    article_type = ARTICLE_TYPE['decizie-cc']

    def summary(self, lines):
        return [{'section': self.article_type['type'], 'title': lines[0]}]


class HgParser(CcParser):

    article_type = ARTICLE_TYPE['hotarare-guvern']


class AdminActParser(HgParser):

    article_type = ARTICLE_TYPE['act-admin-centrala']


class BnrActParser(HgParser):

    article_type = ARTICLE_TYPE['act-bnr']


for cls in [CcParser, HgParser, AdminActParser, BnrActParser]:
    ARTICLE_TYPE[cls.article_type['type']]['parser'] = cls


def parse_tika(lines):
    articles = []

    document_part = 'start'

    lineno = -1
    while lineno < len(lines) - 1:
        lineno += 1
        line = lines[lineno]

        if document_part == 'start':
            if line == 'SUMAR':
                document_part = 'summary'
                summary_section_lines = []
                continue

        if document_part == 'summary':
            if line in HEADLINES2:

                if summary_section_lines:
                    log.debug("(%d) finishing up summary section %r",
                              lineno, summary_section)
                    parser = ARTICLE_TYPE[summary_section]['parser']()
                    articles.extend(parser.summary(summary_section_lines))

                article_type = ARTICLE_TYPE_BY_HEADLINE[line]
                summary_section = article_type['type']
                log.debug("(%d) Summary section %r", lineno, summary_section)
                continue

            summary_section_lines.append(line)
            continue

    return articles


def replace_nbsp(text):
    return text.replace(u'\xa0', ' ')


def cleanspace(text):
    return re.sub(r'\s+', text.replace('\n', ' '), ' ').strip()


class PutBackIterator(object):

    def __init__(self, source):
        self.source = iter(source)
        self.back = []

    def __iter__(self):
        return self

    def next(self):
        if self.back:
            return self.back.pop(-1)
        else:
            return next(self.source)

    def put_back(self, value):
        self.back.append(value)


class MofParser(object):

    _tags = re.compile(r'\<[^>]+\>')
    _headline = re.compile(r'^Anul .* Nr\. (?P<mof_number>\d+)'
                           r'\s+(?P<title>.+)\s+'
                           r'(?P<weekday>\w+), '
                           r'(?P<day>\d{1,2}) (?P<month>\w+) (?P<year>\d{4})$',
                           re.DOTALL)
    _article_title = re.compile(ur'^(?P<number>\d+)\.\s+-\s+'
                                ur'(?P<type>'
                                    ur'Ordonantă de urgentă|'
                                    ur'Hotărâre'
                                    ur')\s+'
                                ur'(?P<summary>privind .*)$')

    def __init__(self, html):
        self.page = HtmlPage(html)

    def parse_article_title(self, title):
        m = self._article_title.match(title)
        if m is not None:
            return m.groupdict()
        return {}

    def save_article_body(self, article, article_body_lines):
        if 'type' in article:
            expect = u'{type} {summary}'.format(**article).lower()
        else:
            expect = u''

        for n, line in enumerate(article_body_lines):
            if not expect:
                break
            if not line:
                continue
            end = line[-15:].lower()
            assert end in expect, (end, expect)
            cut = expect.index(end) + len(end)
            expect = expect[cut:].strip()
        article_body_lines = article_body_lines[n+1:]
        article['body'] = '\n'.join(article_body_lines)

    def parse(self):
        meta = {}
        sections = []
        sections_by_authority = {}
        body_expect = []
        state = 'expect_heading'

        el_iter = PutBackIterator(enumerate(self.page.select('body > div > *')))
        for lineno, el in el_iter:
            text = el.text_content().strip()
            wordtext = cleanspace(text)

            if state == 'expect_heading':
                if 'P A R T E A' in text:
                    meta['heading'] = 'PARTEA I'
                    state = 'expect_identifier'
                continue

            if state == 'expect_identifier':
                if text.startswith("Anul "):
                    meta['identifier'] = text
                    state = 'summary'
                continue

            if state == 'summary':
                if wordtext in HEADLINES:
                    if wordtext in sections_by_authority:
                        log.debug('%d: End of summary', lineno-1)
                        state = 'expect_body_heading'
                        el_iter.put_back((lineno, el))
                        continue
                    section = {
                        'title': wordtext,
                        'articles': [],
                    }
                    sections.append(section)
                    sections_by_authority[section['title']] = section
                    body_expect.append(('section', section, section['title']))

                elif wordtext and wordtext != 'SUMAR':
                    article = {'title': wordtext}
                    article.update(self.parse_article_title(wordtext))
                    section['articles'].append(article)
                    authority = AUTHORITIES[HEADLINES.index(section['title'])]
                    body_expect.append(('article', article, authority))

                continue

            if state == 'expect_body_heading':
                if not body_expect:
                    state = 'done'
                    continue

                if not wordtext:
                    continue

                expected_text = body_expect[0][2]
                if wordtext != expected_text:
                    log.debug("%d: garbage before expected headline: %s...",
                              lineno, wordtext[:30])
                    continue

                if body_expect[0][0] == 'section':
                    log.debug("%d: section %s", lineno, wordtext)
                    body_expect.pop(0)
                    continue

                if body_expect[0][0] == 'article':
                    article = body_expect[0][1]
                    body_expect.pop(0)
                    log.debug("%d: article %s %s (...%s)", lineno,
                              article.get('type'), article.get('number'),
                              article['title'][-30:])
                    article_body_lines = []
                    state = 'article_body'
                    continue

            if state == 'article_body':
                if body_expect and wordtext == body_expect[0][2]:
                    self.save_article_body(article, article_body_lines)
                    article_body_lines = []
                    el_iter.put_back((lineno, el))
                    state = 'expect_body_heading'
                    continue

                article_body_lines.append(wordtext)

        assert not body_expect
        assert state == 'article_body'
        self.save_article_body(article, article_body_lines)

        match = self._headline.match(replace_nbsp(meta['identifier']))
        bits = match.groupdict()
        meta['title'] = cleanspace(bits['title'])
        meta['date'] = date(int(bits['year']),
                            MONTH[bits['month']],
                            int(bits['day']))
        meta['mof_number'] = int(bits['mof_number'])

        return {
            'meta': meta,
            'sections': sections,
        }


def parse(html):
    return MofParser(html).parse()
