from base64 import b64encode
import flask
import requests
import sys


def es_search(text, fields=None, page=1, per_page=20):
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
    search_url = es_url + '/_search'
    search_url += '?from=%d&size=%d' % ((page - 1) * per_page, per_page)
    if fields is not None:
        search_url += '&fields=' + ','.join(fields)
    search_resp = requests.get(search_url, data=flask.json.dumps(search_data))
    assert search_resp.status_code == 200, repr(search_resp)
    return search_resp.json


search_pages = flask.Blueprint('search', __name__, template_folder='templates')


@search_pages.route('/')
def search():
    args = flask.request.args

    q = args.get('q')
    if q:
        page = args.get('page', 1, type=int)
        results = es_search(q, ['year', 'section', 'path'], page=page)
        next_url = flask.url_for('.search', page=page+1, q=q)

    else:
        results = None
        next_url = None

    return flask.render_template('search.html', **{
        'results': results,
        'next_url': next_url,
    })


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
            "document": {
                "properties": {
                    "file": {
                        "type": "attachment",
                        "fields": {
                            "title": {"store": "yes"},
                            "file": {"store": "yes",
                                     "term_vector": "with_positions_offsets"},
                        },
                    },
                },
            },
        }
        attach_resp = requests.put(es_url + '/mof/attachment/_mapping',
                                   data=flask.json.dumps(attachment_config))
        assert attach_resp.status_code == 200, repr(attach_resp)

    @manager.command
    def index(file_path):
        """ Index a file from the repositoy. """
        try:
            from harvest import build_fs_path
            es_url = flask.current_app.config['PUBDOCS_ES_URL']

            (section, year, name) = file_path.split('/')
            fs_path = build_fs_path(file_path)
            index_data = {
                'file': b64encode(fs_path.bytes()),
                'path': file_path,
                'year': int(year),
                'section': int(section[3:]),
            }
            index_resp = requests.post(es_url + '/mof/attachment/' + name,
                                       data=flask.json.dumps(index_data))
            assert index_resp.status_code == 201, repr(index_resp)
        except Exception as exp:
            if index_resp.status_code is not 200:
                raise exp

    @manager.command
    def search(text):
        """ Search the index. """
        print flask.json.dumps(es_search(text), indent=2)

    @manager.command
    def index_section(section, ext):
        """ Bulk index files from specified section and and with corres. extension. """
        import os
        import subprocess
        section_path = flask.current_app.config['PUBDOCS_FILE_REPO'] / section
        total = int(subprocess.check_output(
                        'find %s -name "*%s" | wc -l' %(str(section_path), ext),
                        shell=True))
        indexed = 0
        for year in os.listdir(section_path):
            year_path = section_path / year
            for doc_path in year_path.files():
                if doc_path.ext == ext:
                    name = doc_path.name
                    index('/'.join([section, year, name]))
                    indexed+=1
                    sys.stdout.write("\r%i/%i" %(indexed, total))
                    sys.stdout.flush()
