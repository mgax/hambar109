from path import path
import flask


def create_app():
    from hambar import search
    from hambar import mof_index
    from hambar import model
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


def create_manager(app):
    from flask.ext.script import Manager
    from hambar import search
    from hambar import mof_index
    from hambar import model
    manager = Manager(app)
    search.register_commands(manager)
    manager.add_command('index', mof_index.manager)
    manager.add_command('db', model.model_manager)
    return manager
