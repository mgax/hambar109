web: $PUBDOCS_VENV/bin/python manage.py tornado -p $PORT
worker: $PUBDOCS_VENV/bin/python manage.py worker
redis: redis-server --daemonize no --port $PORT --bind 127.0.0.1 --dir $REDIS_VAR --loglevel notice
es: $PUBDOCS_ES_BIN/elasticsearch -f -Des.network.host=127.0.0.1 -Des.http.port=$PORT -Des.path.data=$ES_PATH_DATA
tika: java -jar $PUBDOCS_TIKA_JAR -s -p $PORT
