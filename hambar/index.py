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

    def doc_ids(**body):
        result = es.search(index=index_name, body=body)
        return [hit['_id'] for hit in result['hits']['hits']]

    def index(doc_id, **body):
        es.index(index=index_name, doc_type='mof', id=doc_id, body=body)

    try:
        index('01', text="foo")
        es.indices.refresh(index=index_name)
        assert doc_ids() == ['01']

    finally:
        es.indices.delete(index_name)
