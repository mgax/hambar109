# encoding: utf-8
from flask.ext.script import Manager
from elasticsearch import Elasticsearch
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

    def count(self):
        return self.es.count(index=self.name)['count']

    def search(self, query):
        return self.es.search(index=self.name, body={'query': query})


index = Index()


@index_manager.command
def initialize():
    index.initialize()


@index_manager.command
def add(number=10):
    count = 0
    for mof in models.Mof.query.filter_by(es_add=True).limit(number):
        index.add(mof.id, {'text': mof.text})
        mof.es_add = False
        count += 1
    models.db.session.commit()
    print("Added %d documents" % count)


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
