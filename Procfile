release: python manage.py migrate
release: python -m spacy download en_core_web_sm
web: gunicorn LirayaWeb.wsgi:application --bind 0.0.0.0:$PORT --log-file -
