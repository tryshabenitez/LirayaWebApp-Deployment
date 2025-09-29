release: python manage.py migrate && python manage.py collectstatic --noinput && python -m spacy download en_core_web_sm
web: gunicorn LirayaWeb.wsgi --log-file -
