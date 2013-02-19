import flask
import requests
import re
import os
import logging
import itertools
from jinja2 import Markup
from jinja2.filters import do_truncate

import utils
from hambar.elastic import ElasticSearch

DEBUG_SEARCH = (os.environ.get('DEBUG_SEARCH') == 'on')

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG if DEBUG_SEARCH else logging.INFO)


es = ElasticSearch(os.environ.get('PUBDOCS_ES_URL'))


search_pages = flask.Blueprint('search', __name__, template_folder='templates')


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
        good = utils.chars_mapping[bad]
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


pat = re.compile(r'([^\x00-\x7F]{2,6})')
def clean(text, debug, year=None):
    """
    Replace custom national characters with their correct representation.
    """
    chars_mapping = dict(utils.chars_mapping)
    #patch with specific year
    if year:
        patch_mapping = getattr(utils,
                                'chars_mapping_%s' %year)
        if patch_mapping:
            chars_mapping.update(patch_mapping)
    for bad, good in chars_mapping.iteritems():
        text = text.replace(bad, good)
    if debug:
        good_cases = []
        perm = []
        for k in [2, 3]:
            perm+=list(itertools.product(utils.good_chars, repeat=k))
        for p in perm:
            good_cases.append(''.join(p))
        for match in pat.finditer(text):
            for case in good_cases:
                if match.group(0) in case:
                    break
            else:
                chars_debug(match, text, True)
    return text


@search_pages.app_template_filter('format_highlight')
def format_highlight(highlights):
    return Markup(' [...] '.join(do_truncate(h) for h in highlights))


@search_pages.route('/')
def search():
    args = flask.request.args

    q = args.get('q')
    if q:
        page = args.get('page', 1, type=int)
        results = es.search(q, ['year', 'section', 'path'], page=page)
        next_url = flask.url_for('.search', page=page + 1, q=q)

    else:
        results = None
        next_url = None

    return flask.render_template('search.html', **{
        'results': results,
        'next_url': next_url,
    })


def _mof_pdf_url(code):
    try:
        section, year, _ = code.split('_', 2)
    except:
        return None
    return '/files/MOF/{0}/{1}/{2}.pdf'.format(section.upper(), year, code)


@search_pages.context_processor
def inject_mof_pdf_url():
    return {
        'mof_pdf_url': _mof_pdf_url,
    }


@search_pages.route('/document/<document_code>')
def document_text(document_code):
    from hambar.model import Document
    session = flask.current_app.extensions['hambar-db'].session
    doc = session.query(Document).filter_by(code=document_code).first()
    if doc is None:
        flask.abort(404)
    return doc.content.text


def register_commands(manager):

    @manager.command
    def flush():
        """ Flush the elasticsearch index """
        es_url = flask.current_app.config['PUBDOCS_ES_URL']

        del_resp = requests.delete(es_url + '/hambar109')
        assert del_resp.status_code in [200, 404], repr(del_resp)

        index_config = {
            "settings": {
                "index": {"number_of_shards": 1,
                          "number_of_replicas": 0},
            },
        }
        create_resp = requests.put(es_url + '/hambar109',
                                   data=flask.json.dumps(index_config))
        assert create_resp.status_code == 200, repr(create_resp)
