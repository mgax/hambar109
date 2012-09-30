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
            "settings" : {
                "index" : {"number_of_shards": 1,
                           "number_of_replicas": 0},
            },
        }
        create_resp = requests.put(es_url + '/mof',
                                   data=flask.json.dumps(index_config))
        assert create_resp.status_code == 200, repr(create_resp)
