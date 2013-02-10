import os
import flask
from redis import Redis
from rq import Worker, Queue, Connection


def _create_connection():
    return Redis(port=int(os.environ['PUBDOCS_REDIS_PORT']))


def initialize(app):
    app.extensions['rq'] = Queue(connection=_create_connection())


def enqueue(func, *args, **kwargs):
    q = flask.current_app.extensions['rq']
    return q.enqueue(func, *args, **kwargs)


def register_commands(manager):
    @manager.command
    def worker():
        listen = ['default']
        conn = _create_connection()
        with Connection(conn):
            worker = Worker(map(Queue, listen))
            worker.work()
