# encoding: utf-8
import re
from datetime import date


MONTH = {
    'martie': 3,
}


tags = re.compile(r'\<[^>]+\>')
def parse(text):
    section = {}
    state = 'expect_heading'
    for line in text.splitlines():
        line = tags.sub('', line).strip()

        if state == 'expect_heading':
            if 'P A R T E A' in line:
                section['heading'] = 'PARTEA I'
                state = 'expect_title'
            continue

        if state == 'expect_title':
            if line:
                section['title'] = line
                state = 'expect_identifier'
            continue

        if state == 'expect_identifier':
            if line:
                section['identifier'] = line
                state = 'expect_content'
                break

    # "Anul 177 (XXI) — Nr. 174 Joi, 19 martie 2009"
    pre_text, date_text = section['identifier'].rsplit(',', 1)
    day, month_name, year = date_text.split()
    section['date'] = date(int(year), MONTH[month_name], int(day))
    section['mof_number'] = int(pre_text.split()[-2])

    return [section]
