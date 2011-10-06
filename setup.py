#/usr/bin/env python
from distutils.core import setup, Extension
from Cython.Distutils import build_ext
import numpy

setup(
    name='django-imagekit',
    version='0.3.6',
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
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
        'Topic :: Utilities'
    ]
)

