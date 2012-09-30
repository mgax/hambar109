from base64 import b64encode
import flask
import requests


def register_commands(manager):

    @manager.command
    def flush():
        """ Flush the elasticsearch index """
        es_url = flask.current_app.config['PUBDOCS_ES_URL']

        del_resp = requests.delete(es_url + '/mof')
        assert del_resp.status_code in [200, 404], repr(del_resp)

        index_config = {
            "settings": {
                "index": {"number_of_shards": 1,
                          "number_of_replicas": 0},
            },
        }
        create_resp = requests.put(es_url + '/mof',
                                   data=flask.json.dumps(index_config))
        assert create_resp.status_code == 200, repr(create_resp)

        attachment_config = {
            "attachment": {
                "properties": {
                    "file": {
                        "type": "attachment",
                        "fields": {
                            "title": {"store": "yes"},
                            "file": {"term_vector": "with_positions_offsets",
                                     "store": "yes"}
                        }
                    }
                }
            }
        }
        attach_resp = requests.put(es_url + '/mof/attachment/_mapping',
                                   data=flask.json.dumps(attachment_config))
        assert attach_resp.status_code == 200, repr(attach_resp)

    @manager.command
    def index(file_path):
        """ Index a file from the repositoy. """
        from harvest import build_fs_path
        es_url = flask.current_app.config['PUBDOCS_ES_URL']

        fs_path = build_fs_path(file_path)
        index_data = {'file': b64encode(fs_path.bytes())}
        index_resp = requests.post(es_url + '/mof/attachment/',
                                   data=flask.json.dumps(index_data))
        assert index_resp.status_code == 201, repr(index_resp)

    @manager.command
    def search(text):
        """ Search the index. """
        es_url = flask.current_app.config['PUBDOCS_ES_URL']
        search_data = {
            "fields": ["title"],
            "query": {
                "query_string": {"query": text},
            },
            "highlight": {
                "fields": {"file": {}},
            },
        }
        search_resp = requests.get(es_url + '/_search',
                                   data=flask.json.dumps(search_data))
        print flask.json.dumps(search_resp.json, indent=2)
