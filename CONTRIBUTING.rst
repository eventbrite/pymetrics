Contributing to PyMetrics
========================

We love your input! We want to make contributing to PyMetrics as easy and transparent as possible, whether it's:

* Reporting a bug
* Discussing the current state of the code
* Submitting a fix
* Proposing new features
* Becoming a maintainer

We Develop with Github
---------------------

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

We Use [Github Flow](https://guides.github.com/introduction/flow/index.html)
-------------------------------------------------------------------------

Pull requests are the best way to propose changes to the codebase. We actively welcome your pull requests:

1. Fork the repo and create your branch from `master`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

We Use Pull Requests
-------------------

We use [Github pull requests](https://github.com/eventbrite/pymetrics/pulls) to accept changes.

Any contributions you make will be under the Apache Software License
-----------------------------------------------------------------

In short, when you submit code changes, your submissions are understood to be under the same [Apache License](http://www.apache.org/licenses/LICENSE-2.0) that covers the project. Feel free to contact the maintainers if that's a concern.

Report bugs using Github's [issue tracker](https://github.com/eventbrite/pymetrics/issues)
---------------------------------------------------------------------------------------

We use GitHub issues to track public bugs. Report a bug by [opening a new issue](https://github.com/eventbrite/pymetrics/issues/new); it's that easy!

Write bug reports with detail, background, and sample code
--------------------------------------------------------

**Great Bug Reports** tend to have:

* A quick summary and/or background
* Steps to reproduce
  * Be specific!
  * Give sample code if you can.
* What you expected would happen
* What actually happens
* Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

License
-------

By contributing, you agree that your contributions will be licensed under its Apache License.

References
----------

This document was adapted from the open-source contribution guidelines for [Facebook's Draft](https://github.com/facebook/draft-js/blob/a9316a723f9e918afde44dea68b5f9f39b7d9b00/CONTRIBUTING.md).

Development Setup
================

1. Clone the repository:
   ```bash
   git clone https://github.com/eventbrite/pymetrics.git
   cd pymetrics
   ```

2. Create Python 3.12 virtual environment (you should ``pip install virtualenvwrapper`` on your system if you have not
   already):
   ```bash
   mkvirtualenv pymetrics
   ```

3. Install the package in development mode:
   ```bash
   pip install -e .[testing]
   ```

4. Run the tests to make sure everything is working:
   ```bash
   pytest
   ```

5. Run linting:
   ```bash
   flake8 pymetrics/ tests/
   mypy pymetrics/
   ```

Code Style
==========

* We use `flake8` for linting
* We use `mypy` for type checking
* We use `black` for code formatting
* We use `isort` for import sorting

You can run all style checks with:
```bash
flake8 pymetrics/ tests/
mypy pymetrics/
black --check pymetrics/ tests/
isort --check-only pymetrics/ tests/
```

Testing
=======

We use `pytest` for testing. To run the tests:

```bash
pytest
```

To run tests with coverage:
```bash
pytest --cov=pymetrics --cov-report=html
```

Pull Request Guidelines
======================

1. Update the documentation if needed
2. Add tests for any new functionality
3. The pull request should work for Python 3.7, 3.8, 3.9, 3.10, 3.11, and 3.12. Check
   that the tests pass for all supported Python versions.
4. Make sure your code follows the style guidelines
5. Update the changelog if needed
