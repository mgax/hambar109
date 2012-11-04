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
