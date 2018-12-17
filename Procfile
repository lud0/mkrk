web: gunicorn mkrk.wsgi --max-requests=500 --preload --timeout=20 --graceful-timeout=5
celery: celery worker -A mkrk -B -E --loglevel=INFO --maxtasksperchild=50 --without-heartbeat --without-gossip --without-mingle
