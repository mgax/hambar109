# encoding: utf-8
import re
from datetime import date
import lxml.html, lxml.cssselect


MONTH = {
    'martie': 3,
}


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


class MofParser(object):

    _tags = re.compile(r'\<[^>]+\>')
    _headline = re.compile(r'^Anul .* Nr\. (?P<mof_number>\d+)'
                           r'\s+(?P<title>.+)\s+'
                           r'(?P<weekday>\w+), '
                           r'(?P<day>\d{1,2}) (?P<month>\w+) (?P<year>\d{4})$',
                           re.DOTALL)

    def __init__(self, html):
        self.page = HtmlPage(html)

    def _iter_lines(self):
        for p in self.page.select('p'):
            yield p.text_content().strip()

    def parse(self):
        meta = {}
        state = 'expect_heading'
        for line in self._iter_lines():
            line = self._tags.sub('', line).strip()

            if state == 'expect_heading':
                if 'P A R T E A' in line:
                    meta['heading'] = 'PARTEA I'
                    state = 'expect_identifier'
                continue

            if state == 'expect_identifier':
                if line.startswith("Anul "):
                    meta['identifier'] = line
                    state = 'expect_content'
                    break

        # "Anul 177 (XXI) — Nr. 174 Joi, 19 martie 2009"
        #pre_text, date_text = meta['title'].rsplit(',', 1)
        #day, month_name, year = date_text.split()
        match = self._headline.match(replace_nbsp(meta['identifier']))
        bits = match.groupdict()
        meta['title'] = re.sub(r'\s+', bits['title'].replace('\n', ' '), ' ').strip()
        meta['date'] = date(int(bits['year']),
                            MONTH[bits['month']],
                            int(bits['day']))
        meta['mof_number'] = int(bits['mof_number'])

        return {
            'meta': meta,
        }


def parse(html):
    return MofParser(html).parse()
