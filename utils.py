# -*- coding: utf-8 -*-
import logging

LOG_FORMAT = "[%(asctime)s] %(name)s %(levelname)s %(message)s"


def set_up_logging():
    stderr = logging.StreamHandler()
    stderr.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.getLogger().addHandler(stderr)
    #logging.getLogger('werkzeug').setLevel(logging.INFO)

good_chars = [
    'ă','â','î','ţ','ş',
    'Ă','Â','Ţ','Ş','Î',
    '”','„','—','«','»',
    '≤','±','Σ','•', '§'
]

chars_mapping = {
    #2005
    '√': 'Ă',
    '¬': 'Â',
    '™': 'Ş',
    '‚': 'â',
    '∫': 'ş',
    '„': 'ă',
    '˛': 'ţ',
    'Ó': 'î',
    'ﬁ': 'Ţ',
    '“': '”',
    'Œ': 'Î',
    #recente
    '\xc8\x98': 'Ş',
    '\xc8\x9a': 'Ţ',
    '\xc8\x9b': 'ţ',
    '\xc8\x99': 'ş',
    '\xc7\x8e': 'ă',
    '\xe2\x80\x93': '—',
    '\xef\xbf\xbd': '...',
}
