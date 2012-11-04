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

    def __init__(self, html):
        self.page = HtmlPage(html)

    def parse(self):
        meta = {}
        section_names = []
        state = 'expect_heading'

        authorities = [
            u"GUVERNUL ROMÂNIEI",
        ]

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
                    if wordtext in section_names:
                        break
                    section_names.append(wordtext)
                continue

        # "Anul 177 (XXI) — Nr. 174 Joi, 19 martie 2009"
        #pre_text, date_text = meta['title'].rsplit(',', 1)
        #day, month_name, year = date_text.split()
        match = self._headline.match(replace_nbsp(meta['identifier']))
        bits = match.groupdict()
        meta['title'] = cleanspace(bits['title'])
        meta['date'] = date(int(bits['year']),
                            MONTH[bits['month']],
                            int(bits['day']))
        meta['mof_number'] = int(bits['mof_number'])

        return {
            'meta': meta,
            'sections': [{'title': n} for n in section_names],
        }


def parse(html):
    return MofParser(html).parse()
