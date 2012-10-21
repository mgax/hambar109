redis: $REDIS_PATH/redis-server --daemonize no --port $PUBDOCS_REDIS_PORT --bind 127.0.0.1 --dir $REDIS_VAR --loglevel notice
web: $PUBDOCS_VENV/bin/gunicorn -b 127.0.0.1:$PUBDOCS_APP_PORT manage:app
worker: $PUBDOCS_VENV/bin/celery worker --app=harvest.celery
es: $PUBDOCS_ES_BIN/elasticsearch -f -Des.network.host=127.0.0.1 -Des.http.port=$PUBDOCS_ES_PORT -Des.path.data=$ES_PATH_DATA
#web_http: $PUBDOCS_VENV/bin/python manage.py runserver -p $PUBDOCS_APP_PORT
