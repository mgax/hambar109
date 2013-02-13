# -*- coding: utf-8 -*-

good_chars = [
    'ă','â','î','ţ','ş',
    'Ă','Â','Ţ','Ş','Î',
    '”','„','—','«','»',
    '≤','±','Σ','•', '§',
    'á', '−', '¹', 'ö', 'é',
    'ó', 'ő', '’', 'ä', 'š',
    'č', '‰', 'ü', 'ï', 'í',
    'Á', 'É', 'è', '□', 'ç',
    'α', 'γ', 'β', 'δ', 'ф',
    'ǿ', 'Ö', '°', 'ʼ', '®',
    '≥', 'λ', 'à', 'ρ', 'Ω',
]

chars_mapping_2000 = {
    'Ã': 'Ă',
    'ã': 'ă',
    'º': 'ş',
    'Ð': '-',
    'ä': '‰',
    '”': '"',
    'Ç': '«',
    'È': '»',
}

chars_mapping_2008 = {
    'ț': 'ţ',
    'ș': 'ş',
    'Ț': 'Ţ',
    '“': '”',
    'ǎ': 'ă',
    '܊': 'ţ',
    'º': 'o',
    'ȃ': 'ă',
}

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
    'ˆ': 'Ă',
    '´': 'Â',
    'Ñ': '—',
    'ª': 'ă',
    'þ': 'ţ',
    'Þ': 'Ţ',
    '¥': '•',
    'Ò': '”',
    'ã': 'ă',
    #recente
    '\xc8\x98': 'Ş',
    '\xc8\x9a': 'Ţ',
    '\xc8\x9b': 'ţ',
    '\xc8\x99': 'ş',
    '\xc7\x8e': 'ă',
    '\xe2\x80\x93': '—',
    '\xef\xbf\xbd': '...',
}
