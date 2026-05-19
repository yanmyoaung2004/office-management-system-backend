python manage.py makemigrations
python manage.py migrate
python manage.py runserver
python manage.py seed_data

uv run --with waitress waitress-serve --port=8000 config.wsgi:application

docker container prune

docker build -t oms-backend:tag .
docker run -p 8000:8000 oms-backend:tag
