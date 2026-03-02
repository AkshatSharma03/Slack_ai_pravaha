web: cd src && python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn akhome.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
worker: cd src && celery -A akhome worker -l info --concurrency 2
