import os
import flask
from flask.ext.script import Manager
from redis import Redis
from rq import Worker, Queue, Connection
from rq.contrib.sentry import register_sentry
from raven import Client


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
    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    listen = ['default']
    conn = _create_connection()
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        if SENTRY_DSN:
            client = Client(SENTRY_DSN)
            register_sentry(client, worker)
        worker.work()
