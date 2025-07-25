#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from invoke import task

from pymetrics import __version__


@task
def clean(ctx):
    """Clean up build artifacts."""
    ctx.run('rm -rf build/')
    ctx.run('rm -rf dist/')
    ctx.run('rm -rf *.egg-info')
    ctx.run('find . -name "*.pyc" -delete')
    ctx.run('find . -name "__pycache__" -delete')


@task
def test(ctx):
    """Run tests."""
    ctx.run('python -m pytest tests/')


@task
def lint(ctx):
    """Run linting."""
    ctx.run('flake8 pymetrics/ tests/')
    ctx.run('mypy pymetrics/')


@task
def build(ctx):
    """Build the package."""
    ctx.run('python setup.py sdist bdist_wheel')


@task
def install(ctx):
    """Install the package in development mode."""
    ctx.run('pip install -e .')


@task
def version(ctx):
    """Print the current version."""
    print(f"pymetrics version: {__version__}")


@task
def tox(ctx):
    """Run tox tests."""
    ctx.run('tox')


@task
def docs(ctx):
    """Build documentation."""
    ctx.run('cd docs && make html')


@task
def check(ctx):
    """Run all checks."""
    lint(ctx)
    test(ctx)
