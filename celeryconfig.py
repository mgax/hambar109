import os

BROKER_URL = 'sqla+sqlite:///celerydb.sqlite'
CELERY_RESULT_BACKEND = "database"
CELERY_RESULT_DBURI = BROKER_URL

#sometimes PUBDOCS_DB_USED is None sometimes is sqlite
if os.environ.get('PUBDOCS_DB_USED')=='sqlite':
    pass
    #BROKER_URL = 'sqla+sqlite:///celerydb.sqlite'
    #CELERY_RESULT_BACKEND = "database"
    #CELERY_RESULT_DBURI = BROKER_URL
else:
    pass
    #BROKER_URL = 'redis://localhost:{PUBDOCS_REDIS_PORT}/0'.format(**os.environ)
    #CELERY_RESULT_BACKEND = BROKER_URL
CELERYD_CONCURRENCY = 1
