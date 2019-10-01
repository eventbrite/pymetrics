PyMetrics - Versatile Metrics Collection for Python
===================================================

Release: |version|

.. image:: https://pepy.tech/badge/pymetrics
    :target: https://pepy.tech/project/pymetrics

.. image:: https://img.shields.io/pypi/l/pymetrics.svg
    :target: https://pypi.python.org/pypi/pymetrics

.. image:: https://api.travis-ci.org/eventbrite/pymetrics.svg
    :target: https://travis-ci.org/eventbrite/pymetrics

.. image:: https://img.shields.io/pypi/v/pymetrics.svg
    :target: https://pypi.python.org/pypi/pymetrics

.. image:: https://img.shields.io/pypi/wheel/pymetrics.svg
    :target: https://pypi.python.org/pypi/pymetrics

.. image:: https://img.shields.io/pypi/pyversions/pymetrics.svg
    :target: https://pypi.python.org/pypi/pymetrics


**PyMetrics** is versatile metrics collection library for Python that encapsulates the collection of counters, gauges,
histograms, and timers into a generic interface with pluggable publishers so that you can helpfully instrument your
applications without suffering vendor lock.

------------

Publishing metrics is a straightforward process involving two steps. First, configure your metrics and publisher(s):

.. code-block:: python

    METRICS_CONFIG = {
        'version': 2,
        'error_logger_name': 'pymetrics',
        'publishers': [
            {
                'path': 'pymetrics.publishers.datadog.DogStatsdPublisher',
                'kwargs': {
                    'host': 'localhost',
                    'port': 8135,
                },
            },
        ],
    }

Then, use a ``pymetrics.recorders.base.MetricsRecorder`` in your application to collect and publish:

.. code-block:: python

    from pymetrics.recorders.default import DefaultMetricsRecorder

    metrics = DefaultMetricsRecorder(config=settings.METRICS_CONFIG)

    metrics.counter('counter.name').increment()

    metrics.gauge('gauge.name', tag_name1='tag_value1', tag_name2='tag_value2').set(12)

    metrics.histogram('histogram.name').set(1730)

    with metrics.timer('timer.name'):
        do_something()

    cumulative_timer = metrics.timer('cumulative_timer.name')
    for item in items:
        do_something_without_timing()
        with cumulative_timer:
            do_something_with_timing()

    metrics.publish_all()

Provided publisher plugins include Statsd, Datadog, Python Logging, SQLite, and a null publisher. Writing your own is
simple and we encourage you to share your work with the community by submitting a pull request.


License
-------

PyMetrics is licensed under the `Apache License, version 2.0 <https://www.apache.org/licenses/LICENSE-2.0>`_.


Table of Contents
-----------------

.. toctree::
   :maxdepth: 2

   user_guide
   reference
   contributing
   history


Indices, Tables, and Searching
------------------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
