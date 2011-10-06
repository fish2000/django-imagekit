#/usr/bin/env python
#from distutils.core import setup, Extension

try:
    from setuptools import setup, Extension
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages
    from setuptools.command.test import test


from Cython.Distutils import build_ext
import numpy

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
        'cython',
        'django-signalqueue>=0.2.8',
        'django-delegate>=0.1.8',
        'pil',
        'ujson',
    ],
    packages=[
        'imagekit',
        'imagekit.colors',
        'imagekit.etc',
        'imagekit.ext',
        'imagekit.management',
        'imagekit.management.commands',
        'imagekit.templatetags',
        'imagekit.utils',
    ],
    package_data={
        'imagekit.colors': [
            'sea.jpg',
            'aggregated/*/*.xml',
            'context/*.txt',
        ],
        'imagekit': [
            'etc/*.csv',
            'etc/*.xls',
            'static/imagekit/css/*.css',
            'static/imagekit/js/*.js',
            'static/imagekit/images/*.png',
            'static/imagekit/images/colorpicker/*.png',
            'static/imagekit/flot/*.js',
            'static/imagekit/flot/*.txt',
            'templates/*.html',
        ],
    },
    
    
    ext_modules=[
        Extension("imagekit.ext.processors", ["imagekit/ext/processors.pyx"]),
    ],
    cmdclass=dict(
        build_ext=build_ext,
    ),
    include_dirs=[
        numpy.get_include(),
        ".",
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
