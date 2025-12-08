release: python manage.py migrate && python manage.py collectstatic --noinput 
web: gunicorn LirayaWeb.wsgi --workers=2 --threads=2 --timeout=300 --log-file -
