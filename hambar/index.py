from flask.ext.script import Manager
from elasticsearch import Elasticsearch

index_manager = Manager()


@index_manager.command
def test():
    test_index_name = 'moftest'
    es = Elasticsearch()

    es.indices.create(
        index=test_index_name,
        body={
            'settings': {
                'analysis': {
                    'analyzer': {
                        'ro': {
                            'type': 'romanian',
                            'filter': ['asciifolding'],
                        },
                    },
                },
            },
        },
    )

    es.index(
        index=test_index_name,
        doc_type='mof',
        id='01',
        body={
            'text': 'foo',
        },
    )

    print es.search()

    es.indices.delete(test_index_name)
