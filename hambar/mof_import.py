import os
import sys
import logging
from contextlib import contextmanager
from datetime import datetime
from collections import defaultdict
from path import path
import simplejson as json
import flask
from flask.ext.script import Manager
from .tika import invoke_tika
from .mof_parser import MofParser
from .queue import enqueue
from .cleanup import fix_national_characters, anonymize_cnp

DEBUG_IMPORT = (os.environ.get('DEBUG_IMPORT') == 'on')


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG if DEBUG_IMPORT else logging.INFO)

manager = Manager()


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


def do_mof_import(code, raw_html, as_json):
    from model import Document, Act, ActType, ImportResult

    with sql_context() as session:
        document = session.query(Document).filter_by(code=code).first()
        if document is None or document.content is None:
            raise RuntimeError("Document text for %r not in database" % code)
        html = document.content.text.encode('utf-8')

        log.info("Parsing %s", code)

        if raw_html:
            print html
            return

        if as_json:
            articles = MofParser(html).parse()
            print json.dumps(articles, indent=2, sort_keys=True)
            return

        try:
            articles = MofParser(html).parse()

        except Exception, e:
            log.exception("Failed to parse document")
            success = False

        else:
            log.info("%d articles found", len(articles))
            success = True
            document = get_or_create(session, Document, code=code)

            for act in document.acts:
                session.delete(act)

            for item in articles:
                act_type = get_or_create(session, ActType,
                                         code=item['section'])
                number = item.get('number')
                act = Act(type=act_type,
                          document=document,
                          ident=number,
                          title=item['title'],
                          text=item['body'],
                          headline=item.get('headline'))
                session.add(act)
                session.flush()
                log.info("New Act %r: %s %s", act.id, act.type.code, act.ident)

            document.import_time = datetime.utcnow()

        session.add(ImportResult(document=document, success=success))


@manager.option('-r', '--raw-html', action='store_true',
                help="Print unparsed HTML")
@manager.option('-j', '--as-json', action='store_true',
                help="Print as json")
@manager.option('name', help="Name of document to be loaded")
@manager.option('-w', '--as-worker', action='store_true',
                help="Run as worker task")
def mof_import(name, raw_html=False, as_json=False, as_worker=False):
    import harvest
    harvest.configure_celery()
    if name == '-':
        for line in sys.stdin:
            mof_import(line.strip(), raw_html, as_json, as_worker)
        return

    if name.endswith('.pdf'):
        name = name.rsplit('.', 1)[0]

    args = (name, raw_html, as_json)

    if as_worker:
        do_mof_import.delay(*args)  # TODO no more celery

    else:
        do_mof_import(*args)


@manager.option('file_path', type=path,
                help="PDF file to import")
@manager.option('document_code',
                help="Code of document (e.g. mof1_2010_0666)")
def document(document_code, file_path):
    from model import Document, Content
    with file_path.open('rb') as f:
        html = ''.join(invoke_tika(f)).decode('utf-8')
    html = anonymize_cnp(fix_national_characters(html))

    with sql_context() as session:
        document_row = get_or_create(session, Document, code=document_code)
        session.add(document_row)
        if document_row.content is not None:
            log.debug("Deleting old content version id=%d",
                      document_row.content.id)
            session.delete(document_row.content)
        document_row.content = Content(text=html)
        session.flush()
        log.debug("New version saved id=%d", document_row.content.id)


@manager.command
def many_documents():
    for line in sys.stdin:
        (document_code, file_path) = line.strip().split(None, 1)
        enqueue(document, document_code, path(file_path))
