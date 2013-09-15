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


if __name__ == '__main__':
    logging.basicConfig(format=LOG_FORMAT)
    logging.getLogger('werkzeug').setLevel(logging.INFO)

    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    if SENTRY_DSN:
        from raven.conf import setup_logging
        from raven.handlers.logging import SentryHandler
        setup_logging(SentryHandler(SENTRY_DSN, level=logging.WARN))

    manager.run()
