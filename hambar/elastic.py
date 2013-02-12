import os
import logging
import requests
import simplejson as json

DEBUG_SEARCH = (os.environ.get('DEBUG_SEARCH') == 'on')

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG if DEBUG_SEARCH else logging.INFO)


class ElasticSearch(object):

    def __init__(self, api_url):
        self.api_url = api_url

    def search(self, text, fields=None, page=1, per_page=20):
        search_data = {
            "fields": ["title"],
            "query": {
                "query_string": {"query": text},
            },
            "highlight": {
                "fields": {"file": {}},
            },
        }
        search_url = self.api_url + '/_search'
        search_url += '?from=%d&size=%d' % ((page - 1) * per_page, per_page)
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
