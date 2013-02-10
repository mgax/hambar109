import os
import flask
from flask.ext.script import Manager
from redis import Redis
from rq import Worker, Queue, Connection


manager = Manager()


def _create_connection():
    return Redis(port=int(os.environ['PUBDOCS_REDIS_PORT']))


def initialize(app):
    app.extensions['rq'] = Queue(connection=_create_connection())


def enqueue(func, *args, **kwargs):
    q = flask.current_app.extensions['rq']
    return q.enqueue(func, *args, **kwargs)


@manager.command
def run():
    listen = ['default']
    conn = _create_connection()
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work()
