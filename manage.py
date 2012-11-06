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
    if 'PUBDOCS_TIKA_PORT' in os.environ:
        app.config['PUBDOCS_TIKA_PORT'] = os.environ['PUBDOCS_TIKA_PORT']
    if os.environ.get('DEBUG'):
        app.debug = True
    app.register_blueprint(search.search_pages)

    @app.route('/crashme')
    def crashme():
        raise RuntimeError("Crashing, as requested.")

    @app.route('/robots.txt')
    def robots_txt():
        return flask.Response('User-agent: *\nDisallow: /\n',
                              content_type='text/plain')

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

else:
    app = create_app()
