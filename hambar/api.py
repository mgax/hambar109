import flask

api_views = flask.Blueprint('api', __name__)


@api_views.before_request
def prepare_db_session():
    flask.g.dbsession = flask.current_app.extensions['hambar-db'].session


@api_views.route('/document/<string:code>.json')
def get_document(code):
    from .model import Document

    doc = flask.g.dbsession.query(Document).filter_by(code=code).first()
    if doc is None:
        flask.abort(404)

    act_data = lambda act: {
        'authority': act.type.label,
        'number': act.ident,
        'title': act.title,
        'body': act.text,
        'headline': act.headline,
    }
    return flask.jsonify(acts=[act_data(act) for act in doc.acts])


@api_views.route('/document/<string:code>.html')
def get_document_html(code):
    from .model import Document

    doc = flask.g.dbsession.query(Document).filter_by(code=code).first()
    if doc is None:
        flask.abort(404)

    return doc.content.text
