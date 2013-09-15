#!/usr/bin/env python

import logging
from path import path
import flask
from flask.ext.script import Manager
from hambar import search
from hambar import mof_index
from hambar import model


LOG_FORMAT = "[%(asctime)s] %(name)s %(levelname)s %(message)s"

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def create_app():
    from hambar.api import api_views

    app = flask.Flask(__name__, instance_relative_config=True)
    app.config.from_pyfile('settings.py', silent=True)

    model.db.init_app(app)

    app.register_blueprint(search.search_pages)

    app.register_blueprint(api_views, url_prefix='/api')

    @app.route('/crashme')
    def crashme():
        raise RuntimeError("Crashing, as requested.")

    @app.route('/robots.txt')
    def robots_txt():
        return flask.Response('User-agent: *\nDisallow: /\n',
                              content_type='text/plain')

    @app.route('/_ping')
    def ping():
        app.extensions['hambar-db'].session.query(model.Document).count()
        mof_index.es.ping()
        return "hambar109 is up\n"

    @app.url_defaults
    def bust_cache(endpoint, values):
        if endpoint == 'static':
            filename = values['filename']
            file_path = path(flask.current_app.static_folder) / filename
            if file_path.exists():
                mtime = file_path.stat().st_mtime
                key = ('%x' % mtime)[-6:]
                values['t'] = key

    return app


manager = Manager(create_app)

search.register_commands(manager)
manager.add_command('index', mof_index.manager)
manager.add_command('db', model.model_manager)


@manager.option('-p', '--port')
def runfcgi(port):
    from flup.server.fcgi import WSGIServer
    app = create_app()
    addr = ('127.0.0.1', int(port))
    WSGIServer(app, debug=app.debug, bindAddress=addr).run()


@manager.option('-p', '--port', type=int, default=5000)
def tornado(port):
    from tornado.web import Application, FallbackHandler
    from tornado.wsgi import WSGIContainer
    from tornado.httpserver import HTTPServer
    from tornado.ioloop import IOLoop

    app = create_app()
    wsgi_container = WSGIContainer(app)
    wsgi_container._log = lambda *args, **kwargs: None
    handlers = [('.*', FallbackHandler, {'fallback': wsgi_container})]
    tornado_app = Application(handlers, debug=DEBUG)
    http_server = HTTPServer(tornado_app)
    http_server.listen(port)
    log.info("Hambar109 Tornado listening on port %r", port)
    IOLoop.instance().start()


if __name__ == '__main__':
    logging.basicConfig(format=LOG_FORMAT)
    logging.getLogger('werkzeug').setLevel(logging.INFO)

    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    if SENTRY_DSN:
        from raven.conf import setup_logging
        from raven.handlers.logging import SentryHandler
        setup_logging(SentryHandler(SENTRY_DSN, level=logging.WARN))

    manager.run()
