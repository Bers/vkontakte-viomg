#!/usr/bin/env python
from distutils.core import setup

version='1.3.5'

setup(
    name='vkontakte_viomg',
    version=version,
    author='Mikhail Korobov, Serhii Maltsev, Eugeny Yablochkin',
    author_email='kmike84@gmail.com, alternativshik@gmail.com',

    packages=['vkontakte_viomg'],
    install_requires=[
        'gevent>=1.0.2',
        'redis>=2.10.5'
    ],

    url='http://bitbucket.org/kmike/vkontakte/',
    license='MIT license',
    description="VK API wrapper",

    long_description="VK api",

    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
