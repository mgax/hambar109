#!/usr/bin/env python

import os
from path import path
import flask
from flask.ext.script import Manager
import requests
import harvest
import search


def create_app():
    app = flask.Flask(__name__, instance_relative_config=True)
    app.config.update({
        'STATIC_LIB_URL': 'http://grep.ro/quickpub/lib',
    })
    app.config.from_pyfile('settings.py', silent=True)
    app.config['PUBDOCS_FILE_REPO'] = path(os.environ.get('PUBDOCS_FILE_REPO')
                                           or app.instance_path)
    if 'PUBDOCS_ES_URL' in os.environ:
        app.config['PUBDOCS_ES_URL'] = os.environ['PUBDOCS_ES_URL']
    app.register_blueprint(search.search_pages)

    @app.route('/static/lib/<path:resource_url>', methods=['GET', 'HEAD'])
    def lib_resource(resource_url):
        if not app.debug:
            flask.abort(404)
        lib_url = app.config['STATIC_LIB_URL'] + '/' + resource_url
        resp = requests.request(flask.request.method, lib_url)
        if resp.status_code != 200:
            flask.abort(resp.status_code)
        headers = {h: v for h, v in resp.headers.items()
                   if h in ['content-type', 'cache-control']}
        return flask.Response(resp.content, headers=headers)

    return app


manager = Manager(create_app)

harvest.register_commands(manager)
search.register_commands(manager)


@manager.option('-p', '--port')
def runfcgi(port):
    from flup.server.fcgi import WSGIServer
    app = create_app()
    addr = ('127.0.0.1', int(port))
    WSGIServer(app, debug=app.debug, bindAddress=addr).run()


if __name__ == '__main__':
    from utils import set_up_logging
    set_up_logging()
    manager.run()
