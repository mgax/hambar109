import os

BROKER_TRANSPORT = 'celery_redis_unixsocket.broker.Transport'
BROKER_HOST = os.environ.get('REDIS_SOCKET')
BROKER_VHOST = 0
CELERYD_CONCURRENCY = 1
