# encoding: utf-8
import flask
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


@index_manager.command
def initialize():
    index = flask.current_app.config['ES_INDEX']
    es = Elasticsearch()
    if es.indices.exists(index):
        print("deleting old index")
        es.indices.delete(index)
    es.indices.create(index=index, body=ES_INDEX_BODY)


@index_manager.command
def add(number=10):
    index = flask.current_app.config['ES_INDEX']
    es = Elasticsearch()
    for mof in models.Mof.query.limit(number):
        es.index(
            index=index,
            doc_type='mof',
            id=mof.id,
            body={'text': mof.text},
        )
    es.indices.refresh(index=index)


def search(query):
    index = flask.current_app.config['ES_INDEX']
    es = Elasticsearch()
    return es.search(index=index, body={'query': {'match': {'text': query}}})


@index_manager.command
def test():
    index_name = 'moftest'
    es = Elasticsearch()
    es.indices.create(index=index_name, body=ES_INDEX_BODY)

    def doc_ids(**body):
        result = es.search(index=index_name, body=body)
        return [hit['_id'] for hit in result['hits']['hits']]

    def index(doc_id, **body):
        es.index(index=index_name, doc_type='mof', id=doc_id, body=body)

    try:
        index('1', text=u"aici am niște cuvinte înțesate de diacritice, "
                        u"unele așa, altele înțepate și greşite.")
        es.indices.refresh(index=index_name)

        assert doc_ids() == ['1']
        assert doc_ids(query={'match': {'text': u"altele"}}) == ['1']
        assert doc_ids(query={'match': {'text': u"greşite"}}) == ['1']
        assert doc_ids(query={'match': {'text': u"gresite"}}) == ['1']
        assert doc_ids(query={'match': {'text': u"greșite"}}) == ['1']

    finally:
        es.indices.delete(index_name)
