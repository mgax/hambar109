"""
Code for cleaning up MOF text when importing.
"""

import re
import itertools
from . import cleanup_defs


def chars_debug(match, text, debug=False):
    class bcolors:
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        OKGREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
    try:
        bad = match.group(0)
        good = cleanup_defs.chars_mapping[bad]
    except KeyError as exp:
        context = (text[match.start()-20:match.start()] +
                   bcolors.FAIL +
                   bad +
                   bcolors.ENDC +
                   text[match.end():match.end()+20]
                  )
        message = '%s\n' %context
        print ('------------'+ bcolors.FAIL +
               repr(bad) +
               bcolors.ENDC + '------------\n')
        print message
        if debug:
            import pdb; pdb.set_trace()


pat = re.compile(ur'([^\u0000-\u007F])')
def clean(text, debug=False, year=None):
    """
    Replace custom national characters with their correct representation.
    """
    chars_mapping = dict(cleanup_defs.chars_mapping)
    #patch with specific year
    if year:
        patch_mapping = getattr(cleanup_defs, 'chars_mapping_%s' %year)
        if patch_mapping:
            chars_mapping.update(patch_mapping)
    for bad, good in chars_mapping.iteritems():
        text = text.replace(bad, good)
    if debug:
        good_cases = []
        perm = []
        for k in [2, 3]:
            perm+=list(itertools.product(cleanup_defs.good_chars, repeat=k))
        for p in perm:
            good_cases.append(''.join(p))
        for match in pat.finditer(text):
            for case in good_cases:
                if match.group(0) in case:
                    break
            else:
                chars_debug(match, text, True)
    return text
