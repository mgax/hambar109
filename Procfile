redis: redis-server --daemonize no --port $PORT --bind 127.0.0.1 --dir $REDIS_VAR --loglevel notice
web: $PUBDOCS_VENV/bin/gunicorn -b 127.0.0.1:$PORT manage:app
worker: $PUBDOCS_VENV/bin/celery worker --app=harvest.celery
es: $PUBDOCS_ES_BIN/elasticsearch -f -Des.network.host=127.0.0.1 -Des.http.port=$PORT -Des.path.data=$ES_PATH_DATA
