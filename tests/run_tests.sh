#!/bin/bash
PYTHONPATH=$PWD:$PWD/..${PYTHONPATH:+:$PYTHONPATH}
export PYTHONPATH

echo "Running django-imagekit tests..."
DJANGO_SETTINGS_MODULE="" /Users/fish/Dropbox/local-instance-packages/Django-1.4-alpha-16955/django/bin/django-admin.py test core --verbosity=2 --settings=settings
