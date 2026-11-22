web: gunicorn app.wsgi --log-file -
release: python manage.py migrate --noinput
push: python manage.py enviar_push --continuo
