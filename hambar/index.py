# encoding: utf-8
from flask.ext.script import Manager
from elasticsearch import Elasticsearch, helpers
from hambar import models

index_manager = Manager()

ES_INDEX_BODY = {
    'settings': {
        'analysis': {
            'analyzer': {
                'mof_text_analyzer': {
                    'tokenizer': 'standard',
                    'filter': ['asciifolding'],
                },
            },
        },
    },
    'mappings': {
        'mof': {
            'properties': {
                'text': {
                    'type': 'string',
                    'index_analyzer': 'mof_text_analyzer',
                    'search_analyzer': 'mof_text_analyzer',
                },
            },
        },
    },
}


class Index(object):

    def __init__(self, name=None):
        self.name = name
        self.doc_type = 'mof'
        self.es = Elasticsearch()

    def init_app(self, app):
        self.name = app.config['ES_INDEX']

    def initialize(self):
        if self.name in self.es.indices.get_aliases():
            print("deleting old index")
            self.drop()
        self.es.indices.create(index=self.name, body=ES_INDEX_BODY)

    def drop(self):
        self.es.indices.delete(self.name)

    def add(self, doc_id, data):
        self.es.index(
            index=self.name,
            doc_type=self.doc_type,
            id=doc_id,
            body=data,
        )
        self.es.indices.refresh(self.name)

    def bulk_add(self, documents):
        rv = helpers.bulk_index(
            client=self.es,
            docs=(
                {
                    '_id': doc_id,
                    '_index': self.name,
                    '_type': self.doc_type,
                    '_source': data,
                }
                for doc_id, data in documents
            ),
            raise_on_error=True,
        )
        self.es.indices.refresh(self.name)

    def count(self):
        return self.es.count(index=self.name)['count']

    def search(self, query):
        return self.es.search(index=self.name, body={'query': query})


index = Index()


@index_manager.command
def initialize():
    index.initialize()


def _get_data(mof):
    return {
        'part': mof.part,
        'year': mof.year,
        'number': mof.number,
        'text': mof.text,
    }


def _iter_docs(number=None, chunk_size=50):
    from sqlalchemy.orm import joinedload
    count = 0
    while True:
        mof_list = (
            models.Mof.query
            .filter_by(es_add=True)
            .options(joinedload(models.Mof.text_row))
            .limit(chunk_size)
            .all()
        )
        if not mof_list:
            return

        for mof in mof_list:
            yield (mof.id, _get_data(mof))
            mof.es_add = False
            count += 1
            if number and count >= number:
                return

        models.db.session.flush()


@index_manager.command
def add(number=10):
    index.bulk_add(_iter_docs(number=int(number)))
    models.db.session.commit()


def search(text):
    return index.search({'match': {'text': text}})


@index_manager.command
def test():
    test_index = Index('moftest')
    test_index.initialize()

    def doc_ids(query):
        result = test_index.search(query)
        return [hit['_id'] for hit in result['hits']['hits']]

    def index(doc_id, **data):
        test_index.add(doc_id, data)

    try:
        index('1', text=u"aici am niște cuvinte înțesate de diacritice, "
                        u"unele așa, altele înțepate și greşite.")

        assert doc_ids({'match': {'text': u"altele"}}) == ['1']
        assert doc_ids({'match': {'text': u"greşite"}}) == ['1']
        assert doc_ids({'match': {'text': u"gresite"}}) == ['1']
        assert doc_ids({'match': {'text': u"greșite"}}) == ['1']

    finally:
        test_index.drop()
