import flask

api_views = flask.Blueprint('api', __name__)


@api_views.before_request
def prepare_db_session():
    flask.g.dbsession = flask.current_app.extensions['hambar-db'].session


@api_views.route('/document/<string:code>')
def get_document(code):
    from .model import Document

    doc = flask.g.dbsession.query(Document).filter_by(code=code).first()
    if doc is None:
        flask.abort(404)

    return flask.jsonify(acts=[{'title': act.title} for act in doc.acts])
