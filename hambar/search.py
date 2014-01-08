import flask
import requests
import os
import logging
from jinja2 import Markup
from jinja2.filters import do_truncate
from hambar import index

DEBUG_SEARCH = (os.environ.get('DEBUG_SEARCH') == 'on')

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG if DEBUG_SEARCH else logging.INFO)

search_pages = flask.Blueprint('search', __name__, template_folder='templates')


@search_pages.app_template_filter('format_highlight')
def format_highlight(highlights):
    return Markup(' [...] '.join(do_truncate(h) for h in highlights))


@search_pages.route('/')
def search():
    args = flask.request.args

    q = args.get('q')
    if q:
        page = args.get('page', 1, type=int)
        #results = es.search(q, ['year', 'section', 'path'], page=page)
        results = index.search(q)
        next_url = flask.url_for('.search', page=page + 1, q=q)

    else:
        results = None
        next_url = None

    return flask.render_template('search.html', **{
        'results': results,
        'next_url': next_url,
    })


@search_pages.route('/about')
def about():
    return flask.render_template('about.html')


def _mof_pdf_url(id):
    from hambar import models
    mof = models.Mof.query.get(id)
    if mof is None or not mof.s3_url:
        return None

    return mof.s3_url


@search_pages.context_processor
def inject_mof_pdf_url():
    return {
        'mof_pdf_url': _mof_pdf_url,
    }


@search_pages.route('/document/<document_code>')
def document_text(document_code):
    from hambar.models import Document
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
