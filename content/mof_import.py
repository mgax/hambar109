import os
import logging
from contextlib import contextmanager
from datetime import datetime
from path import path
import simplejson as json
from .tika import invoke_tika
from .mof_parser import MofParser


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
        for item in acts:
            act_type_row = get_or_create(session, ActType,
                                         code=item['section'])
            number = item.get('number')
            act_row = Act(type=act_type_row,
                          document=document_row,
                          ident=number)
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


def register_commands(manager):

    @manager.option('-r', '--raw-html', action='store_true',
                    help="Print unparsed HTML")
    @manager.option('-j', '--as-json', action='store_true',
                    help="Print as json")
    @manager.option('name', help="Name of document to be loaded")
    def mof_import(name, raw_html=False, as_json=False):
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
