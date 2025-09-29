release: python manage.py migrate
release: python manage.py collectstatic --noinput
release: python -m spacy download en_core_web_sm
web: gunicorn LirayaWeb.wsgi --log-file -
