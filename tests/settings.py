import os

ADMINS = (
    ('test@example.com', 'TEST-R'),
)

import tempfile, os
from django import contrib
tempdata = tempfile.mkdtemp()
approot = os.path.dirname(os.path.abspath(__file__))
adminroot = os.path.join(contrib.__path__[0], 'admin')

MEDIA_ROOT = os.path.join(tempdata, 'media')
MEDIA_URL = '/face/'
STATIC_ROOT = os.path.join(tempdata, 'static', 'admin')[0]
STATIC_URL = '/staticfiles/'
ADMIN_MEDIA_PREFIX = '/admin-media/'

# Django <= 1.2
DATABASE_ENGINE = 'django.db.backends.sqlite3'
DATABASE_NAME = os.path.join(tempdata, 'imagekit-test.db')
TEST_DATABASE_NAME = os.path.join(tempdata, 'imagekit-test.db')

# Django >= 1.3

DATABASES = {
    'default': {
        'NAME': os.path.join(tempdata, 'imagekit-test.db'),
        'TEST_NAME': os.path.join(tempdata, 'imagekit-test.db'),
        'ENGINE': 'django.db.backends.sqlite3',
        'USER': '',
        'PASSWORD': '',
    }
}

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'imagekit',
    'core',
]

DEBUG = True
TEMPLATE_DEBUG = DEBUG
CACHE_BACKEND = 'locmem://'
