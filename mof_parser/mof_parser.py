# encoding: utf-8
import re
import logging
import lxml.html, lxml.cssselect


log = logging.getLogger(__name__)


def nospacelower(text):
    return text.replace(' ', '').lower()


def cleanspace(text):
    return re.sub(r'\s+', text.replace('\n', ' '), ' ').strip()


ARTICLE_TYPES = [

    {'type': 'decizie-cc',
     'group-headline': u"DECIZII ALE CURȚII CONSTITUȚIONALE",
     'origin-headlines': [u"CURTEA CONSTITUȚIONALĂ"]},

    {'type': 'hotarare-guvern',
     'group-headline': u"ORDONANȚE ȘI HOTĂRÂRI ALE GUVERNULUI ROMÂNIEI",
     'origin-headlines': [u"GUVERNUL ROMÂNIEI"]},

    {'type': 'act-admin-centrala',
     'group-headline': (u"ACTE ALE ORGANELOR DE SPECIALITATE ALE "
                        u"ADMINISTRAȚIEI PUBLICE CENTRALE"),
     'origin-headlines': [u"MINISTERUL FINANȚELOR PUBLICE"]},

    {'type': 'act-bnr',
     'group-headline': u"ACTE ALE BĂNCII NAȚIONALE A ROMÂNIEI",
     'origin-headlines': [u"BANCA NAȚIONALĂ A ROMÂNIEI"]},

]

ARTICLE_TYPE = {t['type']: t for t in ARTICLE_TYPES}

ARTICLE_TYPE_BY_HEADLINE = {nospacelower(t['group-headline']): t
                            for t in ARTICLE_TYPES}


spaced_headline = re.compile(r'\b(\w\s){2,}\w\b', re.UNICODE)
multispace = re.compile(r'\s+')


def preprocess(html):
    HEADLINES = [t['group-headline'] for t in ARTICLE_TYPES]

    lines = []
    xml_doc = lxml.html.fromstring(html)
    xml_sel = lxml.cssselect.CSSSelector('body > div > *')
    for el in xml_sel(xml_doc):
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
            replace = lambda m: m.group(0).replace(' ', '')
            almost_fixed_line = spaced_headline.sub(replace, line)
            fixed_line = multispace.sub(' ', almost_fixed_line)
            log.debug('(%d) Fix spaced headline %r -> %r',
                      lineno, line, fixed_line)
            lines[lineno] = fixed_line
            continue

        for headline in HEADLINES:
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


class SummaryParser(object):

    title_end = re.compile(ur'\s+(\.+\s+)?\d+(–\d+)?$')

    def clean_title_end(self, raw_title):
        return self.title_end.sub('', raw_title.strip())

    def make_article(self, match):
        mgroups = match.groupdict()
        title = mgroups['type'] + mgroups['title_start']
        return {
            'number': match.group('number'),
            'section': self.article_type['type'],
            'title': title,
            'headline': mgroups['type'],
        }

    def summary(self, lines):
        articles = []
        current_title = None

        def finish_title():
            raw_title = self.clean_title_end(' '.join(current_title))
            begin_match = self.title_begin.match(raw_title)
            article = self.make_article(begin_match)
            log.debug("Article from summary: %r", article)
            articles.append(article)

        for line in lines:
            if self.title_begin.match(line) is not None:
                if current_title is not None:
                    finish_title()
                current_title = [line]

            else:
                if current_title is None:
                    msg = ("%s can't understand summary first line %r" %
                           (self.__class__.__name__, line))
                    raise RuntimeError(msg)
                current_title.append(line)

        finish_title()

        return articles


class CcParser(SummaryParser):

    article_type = ARTICLE_TYPE['decizie-cc']

    title_begin = re.compile(ur'^(?P<headline>(?P<type>Decizia)'
                                ur' nr. (?P<number>\d+) '
                                ur'din (?P<date>\d{1,2} \w+ \d{4}))\s+'
                             ur'(?P<subtitle>.*)')

    def make_article(self, match):
        return {
            'section': self.article_type['type'],
            'title': match.group(0),
            'subtitle': match.group('subtitle'),
            'headline': match.group('headline'),
        }


class HgParser(SummaryParser):

    article_type = ARTICLE_TYPE['hotarare-guvern']

    title_begin = re.compile(ur'^(?P<number>\d+). — '
                             ur'(?P<type>Ordonanță de urgență|'
                                      ur'Hotărâre)'
                             ur'(?P<title_start>\s+.*)')


class AdminActParser(SummaryParser):

    article_type = ARTICLE_TYPE['act-admin-centrala']

    title_begin = re.compile(ur'^(?P<number>\d+). — '
                             ur'(?P<type>Ordin)'
                             ur'(?P<title_start>\s+.*)')


class BnrActParser(SummaryParser):

    article_type = ARTICLE_TYPE['act-bnr']

    title_begin = re.compile(ur'^(?P<number>\d+). — '
                             ur'(?P<type>Circulară)'
                             ur'(?P<title_start>\s+.*)')


for cls in [CcParser, HgParser, AdminActParser, BnrActParser]:
    ARTICLE_TYPE[cls.article_type['type']]['parser'] = cls


def parse_mof(lines):
    articles = []

    document_part = 'start'
    article_lines = None

    lineno = -1
    while lineno < len(lines) - 1:
        lineno += 1
        line = lines[lineno]
        line_nsl = nospacelower(line)

        if document_part == 'start':
            if line == 'SUMAR':
                document_part = 'summary'
                summary_section_lines = []
                summary_seen_sections = set()
                continue

        if document_part == 'summary':
            if line_nsl in ARTICLE_TYPE_BY_HEADLINE:

                if summary_section_lines:
                    log.debug("(%d) finishing up summary section %r",
                              lineno, summary_section)
                    parser = ARTICLE_TYPE[summary_section]['parser']()
                    articles.extend(parser.summary(summary_section_lines))
                    summary_section_lines[:] = []

                article_type = ARTICLE_TYPE_BY_HEADLINE[line_nsl]
                summary_section = article_type['type']

                if summary_section in summary_seen_sections:
                    log.debug("(%d) Summary over, found section %r again",
                              lineno, summary_section)
                    document_part = 'body'
                    body_article_queue = list(articles)
                    lineno -= 1
                    continue

                summary_seen_sections.add(summary_section)
                log.debug("(%d) Summary section %r", lineno, summary_section)
                continue

            summary_section_lines.append(line)
            continue

        if document_part == 'body':
            if line_nsl in ARTICLE_TYPE_BY_HEADLINE:
                body_section = ARTICLE_TYPE_BY_HEADLINE[line_nsl]['type']
                log.debug("(%d) beginning of body section %r",
                          lineno, body_section)
                continue

            origin_headlines = ARTICLE_TYPE[body_section]['origin-headlines']
            if line_nsl in map(nospacelower, origin_headlines):
                log.debug("(%d) origin headline %r", lineno, line)
                continue

            if body_article_queue:
                next_article = body_article_queue[0]
                next_headline = nospacelower(next_article['headline'])

            else:
                next_article = 'NO SUCH HEADLINE'

            if line and next_headline.startswith(line_nsl):
                log.debug("(%d) possible title match %r %r",
                          lineno, line, next_headline)

                is_match = False
                for n in range(1, 4):
                    concat = nospacelower(' '.join(lines[lineno:lineno+n]))
                    log.debug('Trying %d lines: %r', n, concat)
                    if concat == next_headline:
                        log.debug("It's a match!")
                        lineno += n-1
                        is_match = True
                        break

                if is_match:
                    if article_lines:
                        current_article['body'] = '\n'.join(article_lines)
                    article_lines = []
                    current_article = body_article_queue.pop(0)
                    continue

            article_lines.append(line)
            continue

    if article_lines:
        current_article['body'] = '\n'.join(article_lines)

    if body_article_queue:
        log.warn("Only matched %d out of %d articles",
                 len(articles) - len(body_article_queue), len(articles))

    return articles
