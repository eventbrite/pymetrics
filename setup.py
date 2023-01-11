#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (
    absolute_import,
    unicode_literals,
)

import codecs
import sys

from setuptools import (  # type: ignore
    find_packages,
    setup,
)

from pymetrics import __version__


def readme():
    with codecs.open('README.rst', 'rb', encoding='utf8') as f:
        return f.read()


install_requires = [
    'attrs>=17.4,<22',
    'conformity>=1.26.9,!=1.27.0,<2.0',
    'enum34;python_version<"3.4"',
    'six',
    'typing~=3.7.4;python_version<"3.5"',
]

mypy_require = [
    'mypy~=0.740;python_version>"3.4"',
    'types-six~=0.1.7;python_version>"3.4"',
    'types-mock~=0.1.3;python_version>"3.4"',
    'typing-extensions~=3.10;python_version<"3.8"',
    ]

tests_require = [
    'freezegun',
    'pytest',
    'pytest-cov',
    'pytest-runner',
    'mock',
    'more-itertools~=5.0',  # We must pin this, because 6.0 requires Python 3.
    'importlib-metadata~=5.0;python_version>"3.6"'
] + mypy_require


setup(
    name='pymetrics',
    version=__version__,
    author='Eventbrite, Inc.',
    author_email='opensource@eventbrite.com',
    description='Versatile metrics collection for Python',
    long_description=readme(),
    url='https://github.com/eventbrite/pymetrics',
    packages=list(map(str, find_packages(include=['pymetrics', 'pymetrics.*']))),
    package_data={str('pymetrics'): [str('py.typed')]},  # PEP 561
    zip_safe=False,  # PEP 561
    include_package_data=True,
    install_requires=install_requires,
    tests_require=tests_require,
    setup_requires=['pytest-runner'] if {'pytest', 'test', 'ptr'}.intersection(sys.argv) else [],
    test_suite='tests',
    extras_require={
        'testing': tests_require,
        'docs': ['sphinx~=2.2;python_version>="3.6"'],
    },
    license='Apache 2.0',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Software Development',
    ],
    project_urls={
        'Documentation': 'https://pymetrics.readthedocs.io',
        'Issues': 'https://github.com/eventbrite/pymetrics/issues',
        'CI': 'https://travis-ci.org/eventbrite/pymetrics/',
    },
)
