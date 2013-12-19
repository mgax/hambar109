from flask.ext.script import Manager
from elasticsearch import Elasticsearch

index_manager = Manager()


ES_INDEX_SETTINGS = {
    'analysis': {
        'analyzer': {
            'ro': {
                'type': 'romanian',
                'filter': ['asciifolding'],
            },
        },
    },
}


@index_manager.command
def test():
    index_name = 'moftest'
    es = Elasticsearch()
    es.indices.create(
        index=index_name,
        body={'settings': ES_INDEX_SETTINGS},
    )

    try:
        es.index(
            index=index_name,
            doc_type='mof',
            id='01',
            body={
                'text': 'foo',
            },
        )

        print es.search()

    finally:
        es.indices.delete(index_name)
