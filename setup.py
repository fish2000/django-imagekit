#/usr/bin/env python
import os
import sys
import imagekit

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

if 'publish' in sys.argv:
    os.system('python setup.py sdist upload')
    sys.exit()

setup(
    name='django-imagekit',
    version=imagekit.__version__,
    description='Automated image processing for Django models.',
    author='Justin Driscoll',
    author_email='justin@driscolldev.com',
    maintainer='Alexander Bohn',
    maintainer_email='fish2000@gmail.com',
    license='BSD',
    url='http://github.com/jdriscoll/django-imagekit/',
    install_requires=[
        'django',
        'django-signalqueue>=0.2.8',
        'django-delegate>=0.1.5',
        'pil',
        'ujson',
    ],
    packages=[
        'imagekit',
        'imagekit.management',
        'imagekit.management.commands'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Utilities'
    ]
)
