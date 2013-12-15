from path import path
import flask

core = flask.Blueprint('core', __name__)


@core.route('/crashme')
def crashme():
    raise RuntimeError("Crashing, as requested.")


@core.route('/robots.txt')
def robots_txt():
    return flask.Response('User-agent: *\nDisallow: /\n',
                          content_type='text/plain')


@core.route('/_ping')
def ping():
    from hambar import model
    count = model.db.session.query(model.Mof).count()
    return "hambar109 is up; %d mofs\n" % count


@core.app_url_defaults
def bust_cache(endpoint, values):
    if endpoint == 'static':
        filename = values['filename']
        file_path = path(flask.current_app.static_folder) / filename
        if file_path.exists():
            mtime = file_path.stat().st_mtime
            key = ('%x' % mtime)[-6:]
            values['t'] = key


def create_app():
    from hambar import search
    from hambar import model

    app = flask.Flask(__name__, instance_relative_config=True)
    app.config.from_pyfile('settings.py', silent=True)
    model.db.init_app(app)
    app.register_blueprint(search.search_pages)
    app.register_blueprint(core)
    return app


def create_manager(app):
    from flask.ext.script import Manager
    from hambar import search
    from hambar import model
    from hambar import harvest

    manager = Manager(app)
    search.register_commands(manager)
    manager.add_command('db', model.model_manager)
    manager.add_command('harvest', harvest.harvest_manager)

    @manager.command
    def worker():
        from flask.ext.rq import get_worker
        get_worker().work()

    return manager
