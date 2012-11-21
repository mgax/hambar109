#!/usr/bin/env python

import os
from path import path
import flask
from flask.ext.script import Manager
import requests
import harvest
import search
from content import mof_import


def create_app():
    from content.model import DatabaseForFlask
    from content.api import api_views

    app = flask.Flask(__name__, instance_relative_config=True)
    app.config.update({
        'STATIC_LIB_URL': 'http://grep.ro/quickpub/lib',
    })
    app.config.from_pyfile('settings.py', silent=True)
    app.config['PUBDOCS_FILE_REPO'] = path(os.environ.get('PUBDOCS_FILE_REPO')
                                           or app.instance_path)
    if 'PUBDOCS_ES_URL' in os.environ:
        app.config['PUBDOCS_ES_URL'] = os.environ['PUBDOCS_ES_URL']
    if os.environ.get('DEBUG'):
        app.debug = True

    DatabaseForFlask().initialize_app(app)

    app.register_blueprint(search.search_pages)

    app.register_blueprint(mof_import.mof_import_views, url_prefix='/db')

    app.register_blueprint(api_views, url_prefix='/api')

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
mof_import.register_commands(manager)


@manager.option('-p', '--port')
def runfcgi(port):
    from flup.server.fcgi import WSGIServer
    app = create_app()
    addr = ('127.0.0.1', int(port))
    WSGIServer(app, debug=app.debug, bindAddress=addr).run()


@manager.option('-p', '--port', type=int, default=5000)
def tornado(port):
    from tornado.wsgi import WSGIContainer
    from tornado.httpserver import HTTPServer
    from tornado.ioloop import IOLoop

    app = create_app()
    wsgi_container = WSGIContainer(app)
    wsgi_container._log = lambda *args, **kwargs: None
    http_server = HTTPServer(wsgi_container)
    http_server.listen(port)
    IOLoop.instance().start()


if __name__ == '__main__':
    from utils import set_up_logging
    set_up_logging()
    manager.run()
