# -*- coding: utf-8 -*-
import logging

LOG_FORMAT = "[%(asctime)s] %(name)s %(levelname)s %(message)s"


def set_up_logging():
    stderr = logging.StreamHandler()
    stderr.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.getLogger().addHandler(stderr)
    #logging.getLogger('werkzeug').setLevel(logging.INFO)

chars_mapping = {
    '\xc8\x99': 's',
    '\xc2\xba': 's',
    '\xe2\x88\xab': 's',

    '\xC5\x9E': 'S',
    '\xe2\x84\xa2': 'S',
    '\xc2\xaa': 'S',

    '\xc8\x9b': 't',
    '\xc3\xbe': 't',
    '\xcb\x9b': 't',
    '\xc5\xa3': 't', #ţ

    '\xc4\x82': 'A',
    '\xc3\x82': 'A',
    '\xc8\x98': 'A',
    '\xe2\x88\x9a': 'A',
    '\xc2\xac': 'A',
    '\xc3\x83': 'A',

    '\xc8\x9a': 'T',
    '\xef\xac\x81': 'T',
    '\xc3\x9e': 'T',

    '\xc3\x8e': 'I',
    '\xc5\x92': 'I',

    '\xc3\xae': 'i',
    '\xc3\x93': 'i',

    '\xc3\xa2': 'a',
    '\xc4\x83': 'a',
    '\xc3\xa3': 'a',
    '\xe2\x80\x9a': 'a',

    '\xc3\x91': '--',

    '\xe2\x80\x94': '-',
    '\xc3\x90': '-',
    '\xe2\x80\x93': '-',

    '\xe2\x80\x9c': '"',
    '\xe2\x80\x9d': '"',
    '\xc3\x92': '"',

    '\xee\x80\x85': '...', # 'î': '...'
    '\xc2\xb1': 'u"\u00B1"', #±
    '\xc2\xab': 'u"\u2605"', #★
    '\xc2\xbcC': 'u"\u2103"', #℃
}
