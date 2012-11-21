import os
import sys
import logging
from contextlib import contextmanager
from datetime import datetime
from collections import defaultdict
from path import path
import simplejson as json
import flask
from .tika import invoke_tika
from .mof_parser import MofParser
from harvest import celery


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def all_files(directory):
    for item in directory.listdir():
        if item.isdir():
            for subitem in all_files(item):
                yield subitem
        elif item.isfile():
            yield item


def find_mof(name):
    mof_dir = path(os.environ['MOF_DIR']).abspath()
    for item in all_files(mof_dir):
        if item.name == name + '.pdf':
            return item
    else:
        raise KeyError("Can't find MOF %r" % name)


@contextmanager
def sql_context():
    if flask._app_ctx_stack.top is None:
        # not inside a flask app
        from model import get_session_maker
        Session = get_session_maker()
        session = Session()

    else:
        session = flask.current_app.extensions['hambar-db'].session

    try:
        yield session

    except:
        session.rollback()
        raise

    else:
        session.commit()


def get_or_create(session, cls, **kwargs):
    row = session.query(cls).filter_by(**kwargs).first()
    if row is None:
        row = cls(**kwargs)
        session.add(row)
        session.flush()
        log.info("New %s record %r: %r", cls.__name__, row.id, kwargs)
    return row


def save_document_acts(acts, document_code):
    from model import Act, ActType, Document

    with sql_context() as session:
        document_row = get_or_create(session, Document, code=document_code)

        for act_row in document_row.acts:
            session.delete(act_row)

        for item in acts:
            act_type_row = get_or_create(session, ActType,
                                         code=item['section'])
            number = item.get('number')
            act_row = Act(type=act_type_row,
                          document=document_row,
                          ident=number,
                          title=item['title'])
            session.add(act_row)
            session.flush()
            log.info("New Act record %r: %s %s",
                     act_row.id, act_row.type.code, act_row.ident)

        document_row.import_time = datetime.utcnow()


def save_import_result(document_code, success):
    from model import Document, ImportResult

    with sql_context() as session:
        document_row = get_or_create(session, Document, code=document_code)
        result_row = ImportResult(document=document_row,
                                  success=success,
                                  time=datetime.utcnow())
        session.add(result_row)


@celery.task
def do_mof_import(name, raw_html, as_json):
    pdf_path = find_mof(name)

    log.info("Importing pdf %s", pdf_path)

    with pdf_path.open('rb') as pdf_file:
        html = ''.join(invoke_tika(pdf_file))

    if raw_html:
        print html
        return

    try:
        articles = MofParser(html).parse()

    except Exception, e:
        log.exception("Failed to parse document")

        if as_json:
            return json.dumps([])

        else:
            save_import_result(document_code=name, success=False)

    else:
        log.info("%d articles found", len(articles))

        if as_json:
            print json.dumps(articles, indent=2, sort_keys=True)
            return

        save_document_acts(articles, document_code=name)
        save_import_result(document_code=name, success=True)


def register_commands(manager):

    @manager.option('-r', '--raw-html', action='store_true',
                    help="Print unparsed HTML")
    @manager.option('-j', '--as-json', action='store_true',
                    help="Print as json")
    @manager.option('name', help="Name of document to be loaded")
    @manager.option('-w', '--as-worker', action='store_true',
                    help="Run as worker task")
    def mof_import(name, raw_html=False, as_json=False, as_worker=False):
        if name == '-':
            for line in sys.stdin:
                mof_import(line.strip(), raw_html, as_json, as_worker)
            return

        if name.endswith('.pdf'):
            name = name.rsplit('.', 1)[0]

        args = (name, raw_html, as_json)

        if as_worker:
            do_mof_import.delay(*args)

        else:
            do_mof_import(*args)


mof_import_views = flask.Blueprint('mof_import', __name__,
                                   template_folder='templates')

@mof_import_views.before_request
def prepare_db_session():
    flask.g.dbsession = flask.current_app.extensions['hambar-db'].session


@mof_import_views.route('/import_stats')
def import_stats():
    from .model import Document
    counts = defaultdict(int)
    for doc in flask.g.dbsession.query(Document):
        counts['total'] += 1
        n_acts = len(doc.acts)
        if n_acts:
            counts['success'] += 1
            counts['acts'] += n_acts
    return flask.render_template('import_stats.html', **{
        'counts': dict(counts),
    })


@mof_import_views.route('/import_results')
def import_results():
    from .model import ImportResult
    return flask.render_template('mof_import_status.html', **{
        'import_results': flask.g.dbsession.query(ImportResult),
    })


@mof_import_views.route('/documents/')
def document_list():
    from .model import Document
    return flask.render_template('document_list.html', **{
        'all_documents': flask.g.dbsession.query(Document),
    })


@mof_import_views.route('/documents/<string:document_id>')
def document(document_id):
    from .model import Document
    return flask.render_template('document.html', **{
        'document': flask.g.dbsession.query(Document).get(document_id),
    })
