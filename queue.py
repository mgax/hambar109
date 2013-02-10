import os
from redis import Redis
from rq import Worker, Queue, Connection


def _create_connection():
    return Redis(port=int(os.environ['PUBDOCS_REDIS_PORT']))


def register_commands(manager):
    @manager.command
    def worker():
        listen = ['default']
        conn = _create_connection()
        with Connection(conn):
            worker = Worker(map(Queue, listen))
            worker.work()
