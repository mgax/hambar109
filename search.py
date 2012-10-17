# -*- coding: utf-8 -*-
from base64 import b64encode
import flask
import requests
import sys
import subprocess
import logging
from path import path
from celery import Celery
from celery.signals import setup_logging
from tempfile import NamedTemporaryFile as NamedTempFile
from tempfile import TemporaryFile
#from harvest import appcontext

import utils


celery = Celery()
celery.config_from_object('celeryconfig')

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

def appcontext(func):
    def wrapper(*args, **kwargs):
        import manage
        app = manage.create_app()
        with app.app_context():
            return func(*args, **kwargs)
    return wrapper

@celery.task
@appcontext
def index(file_path):
    """ Index a file from the repositoy. """
    from harvest import build_fs_path
    es_url = flask.current_app.config['PUBDOCS_ES_URL']
    repo = flask.current_app.config['PUBDOCS_FILE_REPO'] / ''

    (section, year, name) = file_path.replace(repo, "").split('/')
    fs_path = build_fs_path(file_path)
    with NamedTempFile(mode='w+b', delete=True) as temp:
        try:
            subprocess.check_call('pdftotext %s %s' %(fs_path, temp.name),
                                  shell=True)
        except Exception as exp:
            log.critical(exp)

        clean(temp.name, False)
        index_data = {
            'file': b64encode(temp.read()),
            'path': file_path,
            'year': int(year),
            'section': int(section[3:]),
        }
        log.info('Indexing %s' %file_path)
        index_resp = requests.post(es_url + '/mof/attachment/' + name,
                                   data=flask.json.dumps(index_data))
        assert index_resp.status_code in [200, 201], repr(index_resp)
        if index_resp.status_code == 200:
            log.info('Skipping. Already indexed!' %file_path)


def clean(file_path, debug):
    """ Index a file from the repositoy. """
    if not debug == 'debug':
        debug = False
    fs_path = path(file_path)
    cursor = 0
    total = fs_path.getsize()
    if debug:
        def custom_handler(err):
            raise Exception(err.object)

        import codecs
        codecs.register_error('custom_handler', custom_handler)

    with fs_path.open('r') as data:
        with NamedTempFile(mode='a', delete=False) as cleaned:
            chunk = data.read(100)
            while chunk:
                while (chunk[-1] not in ['\n'] and
                      (cursor < total)):
                    chunk += data.read(1)
                    cursor += 1
                try:
                    chunk.decode('ascii', 'custom_handler')
                except Exception as exp:
                    #getting here means it needs correction
                    for bad, good in utils.chars_mapping.iteritems():
                        chunk = chunk.replace(bad, good)
                    try:
                        chunk.decode('ascii', 'custom_handler')
                    except Exception as exp:
                        #getting hear means no correction found
                        if debug:
                            import pdb; pdb.set_trace()
                cleaned.write(chunk)
                chunk = data.read(100)
                cursor += len(chunk)
            cleaned.flush()
    with open(cleaned.name, 'rb') as f:
        with fs_path.open('wb') as origin:
            origin.write(f.read())


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
                index.delay(doc_path)
                indexed += 1
                sys.stdout.write("\r%i/%i" % (indexed, total))
                sys.stdout.flush()
