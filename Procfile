web: $PUBDOCS_VENV/bin/python manage.py tornado -p $PORT
worker: $PUBDOCS_VENV/bin/python manage.py queue run
redis: redis-server --daemonize no --port $PORT --bind 127.0.0.1 --dir $REDIS_VAR --loglevel notice --save 60 1 --save 10 100
es: $ES_PREFIX/bin/elasticsearch -f -Des.network.host=127.0.0.1 -Des.http.port=$PORT -Des.path.data=$ES_DATA -Des.node.local=true -Des.discovery.zen.ping.multicast.enabled=false
tika: java -jar $PUBDOCS_TIKA_JAR -s -p $PORT
rqdashboard: $PUBDOCS_VENV/bin/rq-dashboard -b 127.0.0.1 -p $PORT -P $PUBDOCS_REDIS_PORT
