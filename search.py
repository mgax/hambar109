# -*- coding: utf-8 -*-
from base64 import b64encode
import flask
import requests
import os
import sys
import subprocess
import logging
import socket
from path import path
from celery.signals import setup_logging
from tempfile import NamedTemporaryFile as NamedTempFile
from tempfile import TemporaryFile
from harvest import appcontext, celery

import utils
from html2text import html2text


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


def invoke_tika(data_file, host='127.0.0.1', port=9999, buffer_size=16384):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    while True:
        chunk = data_file.read(buffer_size)
        if not chunk:
            break
        sock.send(chunk)
    sock.shutdown(socket.SHUT_WR)
    while True:
        chunk = sock.recv(buffer_size)
        if not chunk:
            break
        yield chunk
    sock.close()


@celery.task
@appcontext
def index(file_path, debug=False):
    """ Index a file from the repositoy. """
    from harvest import build_fs_path
    es_url = flask.current_app.config['PUBDOCS_ES_URL']
    repo = flask.current_app.config['PUBDOCS_FILE_REPO'] / ''
    tika_port = flask.current_app.config['PUBDOCS_TIKA_PORT']

    (section, year, name) = file_path.replace(repo, "").split('/')
    fs_path = build_fs_path(file_path)
    with NamedTempFile(mode='w+b', delete=True) as temp:
        try:
            with open(fs_path, 'rb') as pdf_file:
                for chunk in invoke_tika(pdf_file, port=tika_port):
                    temp.write(chunk)
                temp.seek(0)

        except Exception as exp:
            log.critical(exp)
        from time import time
        start = time()
        clean(temp.name, debug)
        duration = time() - start
        with open(temp.name) as tmp:
            text = tmp.read()
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
        good = utils.chars_mapping.get(bad, '???')
    finally:
        old = (text[match.start()-20:match.start()] +
               bcolors.FAIL +
               bad +
               bcolors.ENDC +
               text[match.end():match.end()+20]
              )
        new = (text[match.start()-20:match.start()] +
               bcolors.OKGREEN +
               good +
               bcolors.ENDC +
               text[match.end():match.end()+20]
              )
        message = '%s\n%s\n' %(old, new)
        print ('------------'+ bcolors.FAIL +
               repr(bad) +
               bcolors.ENDC + '------------\n')
        print message
        if debug:
            import pdb; pdb.set_trace()


import re
pat3 = re.compile(r'([^\x00-\x7F][^\x00-\x7F][^\x00-\x7F])')
pat2 = re.compile(r'([^\x00-\x7F][^\x00-\x7F])')
def clean(file_path, debug):
    """ Index a file from the repositoy. """
    with open(file_path, 'r') as data:
        with NamedTempFile(mode='a', delete=False) as cleaned:
            text = data.read()
            for bad, good in utils.chars_mapping.iteritems():
                text = text.replace(bad, good)
            if debug:
                for match in pat3.finditer(text):
                    chars_debug(match, text, True)
                for match in pat2.finditer(text):
                    chars_debug(match, text, True)

    with open(cleaned.name, 'rb') as f:
        with open(file_path, 'wb') as origin:
            text = text.decode('ISO-8859-1')
            origin.write(text.encode('UTF8'))


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

    @manager.command
    def index_file(file_path, debug):
        index(file_path, debug)

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
            for doc_path in year_path.files():
                name = doc_path.name
                if debug:
                    index(doc_path, debug)
                else:
                    index.delay(doc_path)
                indexed += 1
                sys.stdout.write("\r%i/%i" % (indexed, total))
                sys.stdout.flush()

        print ' done'
