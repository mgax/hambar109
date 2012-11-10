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
from celery.signals import setup_logging
from tempfile import NamedTemporaryFile as NamedTempFile
from tempfile import TemporaryFile
from harvest import appcontext, celery
from pyquery import PyQuery as pq

import utils
from html2text import html2text

from content.tika import invoke_tika


@setup_logging.connect
def configure_worker(sender=None, **extra):
    from utils import set_up_logging
    set_up_logging()

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def es_search(text, fields=None, page=1, per_page=20):
    es_url = flask.current_app.config['PUBDOCS_ES_URL']
    search_data = {
        "fields": ["title"],
        "query": {
            "query_string": {"query": text},
        },
        "highlight": {
            "fields": {"file": {}},
        },
    }
    search_url = es_url + '/_search'
    search_url += '?from=%d&size=%d' % ((page - 1) * per_page, per_page)
    if fields is not None:
        search_url += '&fields=' + ','.join(fields)
    search_resp = requests.get(search_url, data=flask.json.dumps(search_data))
    assert search_resp.status_code == 200, repr(search_resp)
    return search_resp.json


search_pages = flask.Blueprint('search', __name__, template_folder='templates')


@celery.task
@appcontext
def index(file_path, debug=False):
    """ Index a file from the repositoy. """
    from harvest import build_fs_path
    es_url = flask.current_app.config['PUBDOCS_ES_URL']
    repo = flask.current_app.config['PUBDOCS_FILE_REPO'] / ''

    (section, year, name) = file_path.replace(repo, "").split('/')
    fs_path = build_fs_path(file_path)
    with NamedTempFile(mode='w+b', delete=True) as temp:
        start = time()
        try:
            with open(fs_path, 'rb') as pdf_file:
                for chunk in invoke_tika(pdf_file):
                    temp.write(chunk)
                temp.seek(0)

        except Exception as exp:
            log.critical(exp)
        text = clean(temp.name, debug)
        index_data = {
            'file': b64encode(text),
            'path': file_path,
            'year': int(year),
            'section': int(section[3:]),
        }
        index_resp = requests.post(es_url + '/mof/attachment/' + name,
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
def clean(file_path, debug):
    """ Index a file from the repositoy. """
    import itertools
    with open(file_path, 'r') as data:
        text = data.read()
        for bad, good in utils.chars_mapping.iteritems():
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


@search_pages.route('/')
def search():
    args = flask.request.args

    q = args.get('q')
    if q:
        page = args.get('page', 1, type=int)
        results = es_search(q, ['year', 'section', 'path'], page=page)
        next_url = flask.url_for('.search', page=page + 1, q=q)

    else:
        results = None
        next_url = None

    return flask.render_template('search.html', **{
        'results': results,
        'next_url': next_url,
    })

@search_pages.route('/stats')
def stats():
    return flask.render_template('stats.html')

@search_pages.route('/stats_json')
def stats_json():
    repo_path = flask.current_app.config['PUBDOCS_FILE_REPO'] / 'MOF1'
    tree = construct_tree(repo_path)
    return flask.jsonify(tree)


def construct_tree(fs_path):
    def recursion(loc):
        children = []
        if loc.isdir():
            for item in loc.dirs():
                if item.dirs():
                    children += [recursion(item)]
                else:
                    children.append({"name": item.name.upper(), "size": item.size})
        return {"name": loc.name.upper(), "children": children}
    return recursion(fs_path)


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

        del_resp = requests.delete(es_url + '/mof')
        assert del_resp.status_code in [200, 404], repr(del_resp)

        index_config = {
            "settings": {
                "index": {"number_of_shards": 1,
                          "number_of_replicas": 0},
            },
        }
        create_resp = requests.put(es_url + '/mof',
                                   data=flask.json.dumps(index_config))
        assert create_resp.status_code == 200, repr(create_resp)

        attachment_config = {
            "document": {
                "properties": {
                    "file": {
                        "type": "attachment",
                        "fields": {
                            "title": {"store": "yes"},
                            "file": {"store": "yes",
                                     "term_vector": "with_positions_offsets"},
                        },
                    },
                },
            },
        }
        attach_resp = requests.put(es_url + '/mof/attachment/_mapping',
                                   data=flask.json.dumps(attachment_config))
        assert attach_resp.status_code == 200, repr(attach_resp)

    @manager.command
    def search(text):
        """ Search the index. """
        print flask.json.dumps(es_search(text), indent=2)

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
                    index.delay(doc_path)
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
