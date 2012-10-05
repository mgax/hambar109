import os


BROKER_URL = 'redis://localhost:{PUBDOCS_REDIS_PORT}/0'.format(**os.environ)
CELERY_RESULT_BACKEND = BROKER_URL
CELERYD_CONCURRENCY = 1
