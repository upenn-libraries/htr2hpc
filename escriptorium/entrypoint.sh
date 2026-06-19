#!/bin/sh


echo "Waiting for postgres..."
while ! nc -z $SQL_HOST $SQL_PORT; do
    sleep 0.1
done
echo "PostgreSQL started"

python manage.py migrate

# static files
python manage.py collectstatic --no-input

# Update Site instance with ESCRIPTORIUM_HOST
# set ESCRIPTORIUM_HOST to localhost if not already set
: "${ESCRIPTORIUM_HOST:=localhost}"
python manage.py shell <<EOF
from django.contrib.sites.models import Site
from django.conf import settings
s = Site.objects.get(pk=settings.SITE_ID)
s.domain = "${ESCRIPTORIUM_HOST}"
s.name = "${ESCRIPTORIUM_HOST}"
s.save()
EOF

exec "$@"