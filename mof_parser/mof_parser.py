# encoding: utf-8
import re
from datetime import date
import lxml.html, lxml.cssselect


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

    def parse(self):
        meta = {}
        sections = []
        sections_by_authority = {}
        state = 'expect_heading'

        for el in self.page.select('body > div > *'):
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
                        break
                    section = {
                        'title': wordtext,
                        'articles': [],
                    }
                    sections.append(section)
                    sections_by_authority[section['title']] = section

                elif wordtext and wordtext != 'SUMAR':
                    article = {'title': wordtext}
                    article.update(self.parse_article_title(wordtext))
                    section['articles'].append(article)

                continue

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
