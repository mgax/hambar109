import sys
import os
from flask.ext.script import Manager
from .mof_import import sql_context
from .elastic import ElasticSearch
from .queue import enqueue


manager = Manager()

es = ElasticSearch(os.environ.get('PUBDOCS_ES_URL'))


@manager.option('document_code',
                help="Code of document (e.g. mof1_2010_0666)")
def document(document_code):
    from model import Document
    with sql_context() as session:
        doc = session.query(Document).filter_by(code=document_code).first()
        if doc is None:
            raise RuntimeError("Document %r not found" % document_code)
        es.index_document(doc)


@manager.command
def many_documents():
    for line in sys.stdin:
        document_code = line.strip()
        enqueue(document, document_code)
