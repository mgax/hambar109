# -*- coding: utf-8 -*-
from base64 import b64encode
import flask
import requests
import re
import os
import sys
import json
import subprocess
import logging
from path import path
from time import time
from tempfile import NamedTemporaryFile as NamedTempFile
from tempfile import TemporaryFile
from harvest import appcontext
from pyquery import PyQuery as pq
from jinja2 import Markup
from jinja2.filters import do_truncate

import utils
from html2text import html2text
from hambar.tika import invoke_tika
from hambar.elastic import ElasticSearch

DEBUG_SEARCH = (os.environ.get('DEBUG_SEARCH') == 'on')

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG if DEBUG_SEARCH else logging.INFO)


es = ElasticSearch(os.environ.get('PUBDOCS_ES_URL'))


search_pages = flask.Blueprint('search', __name__, template_folder='templates')


@appcontext
def index(file_path, debug=False):
    """ Index a file from the repositoy. """
    from harvest import build_fs_path
    es_url = flask.current_app.config['PUBDOCS_ES_URL']
    repo = flask.current_app.config['PUBDOCS_FILE_REPO'] / ''

    name = file_path.replace(repo, "").split('/')[-1]
    m = re.match(r'^mof1_(?P<year>\d{4})_\d+\.pdf$', name)
    section = 'mof1'
    try:
        year = int(m.group('year'))
    except AttributeError:
        year = 0
    fs_path = build_fs_path(file_path)
    with NamedTempFile(mode='w+b', delete=True) as temp:
        start = time()
        try:
            with open(fs_path, 'rb') as pdf_file:
                for chunk in invoke_tika(pdf_file):
                    temp.write(chunk)
                temp.seek(0)

        except Exception as exp:
            log.exception("Exception when calling tika")
            return
        text = clean(temp.name, debug, year=year)
        index_data = {
            'text': text,
            'path': file_path,
            'year': int(year),
            'section': int(section[3:]),
        }
        index_resp = requests.post(es_url + '/hambar109/mof/' + name,
                                   data=flask.json.dumps(index_data))
        assert index_resp.status_code in [200, 201], repr(index_resp)
        if index_resp.status_code == 200:
            log.info('Skipping. Already indexed!')
        else:
            duration = time() - start
            log.info('%s[indexed in %f]' %(fs_path.name, duration))


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


import re
pat = re.compile(r'([^\x00-\x7F]{2,6})')
def clean(file_path, debug, year=None):
    """ Index a file from the repositoy. """
    import itertools
    with open(file_path, 'r') as data:
        text = data.read()
        chars_mapping = utils.chars_mapping
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


@search_pages.route('/stats')
def stats():
    return flask.render_template('stats.html')


@search_pages.route('/stats_json/<int:year>')
@search_pages.route('/stats_json')
def stats_json(year=None):
    dir_path = flask.current_app.config['PUBDOCS_FILE_REPO'] / 'MOF1'
    with_files = False
    if year and (dir_path / str(year)).exists():
        dir_path = dir_path / str(year)
        with_files=True
    tree = construct_tree(dir_path, with_files)
    return flask.jsonify(tree)


@search_pages.route('/document/<document_code>')
def document_text(document_code):
    from hambar.model import Document
    session = flask.current_app.extensions['hambar-db'].session
    doc = session.query(Document).filter_by(code=document_code).first()
    if doc is None:
        flask.abort(404)
    return doc.content.text


def construct_tree(fs_path, with_files=False):
    def recursion(loc, with_files):
        children = []
        if loc.isdir():
            if with_files:
                for f in loc.files():
                    children.append({"name": f.name.upper(), "size": f.size})
            for item in loc.dirs():
                if with_files:
                    children += [recursion(item)]
                else:
                    if item.dirs():
                        children += [recursion(item)]
                    else:
                        children.append({"name": item.name.upper(), "size": len(item.files())})
        return {"name": loc.name.upper(), "children": children}
    return recursion(fs_path, with_files)


def available_files(location):
    import os
    files=[]
    def walker(arg, dirname, names):
        files.append(names)
    os.path.walk(location, walker, '')
    return files



def _load_json(name):
    with open(os.path.join(os.path.dirname(__file__), name), "rb") as f:
        return json.load(f)

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

    @manager.command
    def search(text):
        """ Search the index. """
        print flask.json.dumps(es.search(text), indent=2)

    @manager.option('-d', '--debug', action='store_true')
    @manager.option('-p', '--path')
    def index_file(path, debug):
        index(path, debug)

    @manager.option('-d', '--debug', action='store_true')
    @manager.option('-s', '--section', default=None)
    def index_section(section, debug):
        """ Bulk index pdfs from specified section. """
        import os
        import subprocess

        section_path = flask.current_app.config['PUBDOCS_FILE_REPO'] / section
        args = 'find %s -name "*.pdf" | wc -l' % (str(section_path))
        total = int(subprocess.check_output(args, shell=True))
        indexed = 0
        for year in os.listdir(section_path):
            year_path = section_path / year
            doc_paths = [dp for dp in year_path.files() if dp.endswith('pdf')]
            for doc_path in doc_paths:
                name = doc_path.name
                if debug:
                    index(doc_path, debug)
                else:
                    index.delay(doc_path)  # TODO celery is gone
                indexed += 1
                sys.stdout.write("\r%i/%i" % (indexed, total))
                sys.stdout.flush()

        print ' done'

    no_pat = re.compile('(?<=^)\d+')
    name_pat = re.compile('(?<=\xe2\x80\x94 Lege privind ).+(?= \.)')
    interval_pat = re.compile('(\d+)\xe2\x80\x93(\d+)$')
    @manager.command
    def extract_laws_summary(file_path):
        from harvest import build_fs_path
        no = name = start_pg = end_pg = None
        laws = []
        fs_path = build_fs_path(file_path)
        with NamedTempFile(mode='w+b', delete=False) as temp:
            command = ('pdf2htmlEX --process-nontext 0 --dest-dir '
                       '/tmp %s %s' %(fs_path, temp.name.split('/')[-1]))
            subprocess.check_call(command, shell=True)
        with open(temp.name, 'rb') as tmp:
            html = pq(tmp.read())
            for div in html('#p1 .b .h3'):
                sum_entry = div.text_content()
                if 'Lege privind' in sum_entry:
                    if no_pat.search(sum_entry):
                        import pdb; pdb.set_trace()
                        no = no_pat.search(sum_entry).group(0)
                    if name_pat.search(sum_entry):
                        name = name_pat.search(sum_entry).group(0)
                    if interval_pat.search(sum_entry):
                        start_pg = interval_pat.search(sum_entry).group(1)
                        end_pg = interval_pat.search(sum_entry).group(2)
                    laws.append([no, name, start_pg, end_pg])
        os.remove(temp.name)
        return laws
