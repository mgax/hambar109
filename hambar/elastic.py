import os
import logging
import requests
import simplejson as json
from jinja2.filters import do_striptags


DEBUG_SEARCH = (os.environ.get('DEBUG_SEARCH') == 'on')

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG if DEBUG_SEARCH else logging.INFO)


class ElasticSearch(object):

    def __init__(self, api_url, index_name='main'):
        self.api_url = api_url
        self.index_name = index_name

    def ping(self):
        resp = requests.get(self.api_url)
        assert resp.status_code == 200

    def search(self, text, fields=None, page=1, per_page=20):
        search_data = {
            "query": {
                "query_string": {
                    "query": text,
                },
            },
            "highlight": {
                "fields": {
                    "content": {
                        "fragment_size": 150,
                        "number_of_fragments": 3,
                    },
                },
            },
        }
        search_url = ('{self.api_url}/{self.index_name}/document/_search'
                      '?from={start}&size={per_page}'
                      .format(self=self,
                              start=(page - 1) * per_page,
                              per_page=per_page))
        if fields is not None:
            search_url += '&fields=' + ','.join(fields)
        search_json = json.dumps(search_data)
        log.debug("search: %s", search_json)
        search_resp = requests.get(search_url, data=search_json)
        if search_resp.status_code != 200:
            log.error("Error response: %r", search_resp.text)
            raise RuntimeError("ElasticSearch query failed")
        assert search_resp.status_code == 200, repr(search_resp)
        return search_resp.json

    def index_document(self, doc):
        put_url = ('{self.api_url}/{self.index_name}/document/{doc.code}'
                   .format(self=self, doc=doc))
        publication, year, _ = doc.code.split('_', 2)
        data_json = json.dumps({
            'content': do_striptags(doc.content.text),
            'publication': publication,
            'year': int(year),
        })
        resp = requests.put(put_url, data=data_json)
        if resp.status_code not in [200, 201]:
            log.error("Error while indexing %s: %r", doc.code, resp.text)
            raise RuntimeError("ElasticSearch indexing failed")
