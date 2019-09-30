PyMetrics User Guide
====================

.. contents:: Contents
   :depth: 3
   :local:
   :backlinks: none

PyMetrics consists of four key concepts: Instruments, recorders, publishers, and configuration. Instruments are the
concept that encapsulate the "what" of metrics—counters, timers, gauges, and histograms. Recorders are objects used to
manage the creation and recording of instruments and send those metrics to configured publishers. Publishers are the
pluggable tools that understand vendor-specific metrics consumers or datastores and know how to publish metrics to
those consumers or datastores. Finally, configuration is what ties it all together.


Instruments
-----------

Instruments encapsulate the core concept of PyMetrics. All instruments extend ``pymetrics.instruments.Metric`` and
provide different means for setting or calculating values. You can obtain the value of any instrument by accessing the
``value`` property.

All instruments must have a name. Additionally, all instruments also support the notion of tags, or arbitrary "notes"
that supplement the name. Tags are passed to the constructor as keyword arguments other than those the constructor
already understands, and can also be modified with the ``tags`` attribute, which is a dictionary of tag names to tag
values. Tags can be strings, integers, floats, Booleans, or ``None`` (a special case where the tag is just "present"
and a value is meaningless). However, you should note that not all publishers support tags: The logging and Datadog
publishers support tags, but the Statsd and SQL publishers do not (at this time). Publishers that do not support tags
will silently ignore them, so you can feel safe to use them any time without worrying about errors.


Counters
++++++++

Counters are represented with the ``pymetrics.instruments.Counter`` class. Counters can be incremented with the
``increment`` method, which by default increments by 1 but accepts an argument to increment by more. Counters have a
default value of 0 unless you pass a different default value to the constructor. You can also ``reset`` a counter; with
no argument, it resets to the default value of 0 or as specified in the constructor, but accepts an argument to reset
to that value, instead.

Another feature of counters is that they can be recorded "around" function/method calls, so that each call to the
function or method records a counter with value 1. More about this below in `Decorators`_.

Conceptually, counters are about counting discrete things or events. Notably, counters are often used to record the
number of times some event happens, and typically consumers of counters use them to determine rates (events per second,
etc.).

.. code-block:: python

    counter = Counter('my.counter')  # 0
    counter.increment()  # 1
    counter.increment(3)  # 4
    counter.reset()  # 0
    counter.reset(5)  # 5


Histograms
++++++++++

Histograms are represented with the ``pymetrics.instruments.Histogram`` class. The concept of histograms involves the
ability to record an arbitrary number of something per event. While counters are often used to count events, histograms
are used to count something about an individual event. For example, histograms may be used to record request or
response size in bytes. The consumers to which your metrics are published can then calculate average, p75, p90, p95,
etc., using the values from these histograms.

Histograms have an initial value of 0 unless you pass a different initial value to the constructor. You can also set
the value of a histogram by calling the ``set`` method. Histograms cannot be recorder "around" function/method calls.

.. code-block:: python

    histogram = Histogram('my.histogram', initial_value=5, tag1='value1')  # 5
    histogram.set(10)  # 10


Timers
++++++

Timers are represented with the ``pymetrics.instruments.Timer`` class, and they extend ``Histogram``. Timers are the
special-case histogram that understands the passage of time and sets its own value based on that. Like histograms, they
record the number of something about an individual event, but understand that this particular something is time. As
such, timers *can* be recorded "around" function/method calls (see `Decorators`_).

Timers are perhaps the most complex of all the metric types:

* The ``initial_value`` constructor argument defaults to 0, and this causes the ``value`` property to return ``None``.
  It is the only metric with this behavior, and it is an indicator that "the timer has not recorded anything." This is
  an important distinction, since very-fast events could appear as taking 0 time, and those are not to be confused with
  timers that have not recorded anything. Publishers do not (and custom publishers should not) publish timers with a
  ``value`` of ``None``. Recorders should not send timers with a ``value`` of ``None`` and, instead, should hold them
  over to the next publication time.
* Timers can be started and stopped. You start a timer by calling ``start`` and stop it by calling ``stop``.
  Alternatively, you can use a timer as a context manager using the ``with`` syntax, and that timer will be started and
  stopped around the nested code block. Timers can also be re-entered: Once a timer has been stopped, it can be
  started again and will begin accumulating more time until it is stopped again. This has a cumulative effect, not a
  resetting effect. Constructing a timer starts it, but it is harmless to start it again after constructing it (the
  start time is just reset). If you try to stop a timer that has not been started, it will cause an error.
* Timers have a ``resolution`` constructor argument that should be a member of the ``TimerResolution`` enum. This
  determines how the timer is represented in ``value``. Options are ``MILLISECONDS`` (the default, for the longest
  events), ``MICROSECONDS`` (for relatively fast events), and ``NANOSECONDS`` (for the fastest possible events).
* The ``value`` property will first check if the timer has recorded elapsed time. If it has and is not currently
  running, ``value`` returns that elapsed time multiplied by the resolution and then rounded. If the timer does not
  have elapsed time but does have a non-zero initial value or a value set with ``set``, ``value`` returns that initial
  or set value without considering the resolution. Otherwise, ``value`` returns ``None``.

.. code-block:: python

    timer = Timer('timer.1')  # None
    timer.start()
    timer.value  # None
    do_something()  # takes 0.005283 seconds
    timer.stop()
    timer.value  # 5

    with timer:
        do_something_else()  # takes 0.009576 seconds

    timer.value  # 15

    timer.start()
    timer.value  # None
    do_something()  # takes 0.001 seconds
    timer.stop()
    timer.value  # 16

    with Timer('timer.2', resolution=TimerResolution.MICROSECONDS, tag2='value2') as timer2:
        timer2.tags['tag3'] = 'value3'
        do_something_fast()  # takes 0.000003153 seconds

    timer2.value  # 3


Gauges
++++++

Gauges, represented by ``pymetrics.instruments.Gauge``, are a way of measuring the size of something. This differs
from counters, which count events, and histograms, which count a value per-event, in that it isn't linked to events.
Gauges are a lot like the fuel tank gauge in your automobile (or the battery indicator in your electric automobile),
and are often used to measure things like queues, pools, memory, CPU, and disk space (consumed or free). Note, however,
that some consumers, like Datadog, do not have good support for distributed gauges that use only names. If you want to
record a gauge with the same name across many servers to measure a global pool, queue, etc., you need to include tags
on each server in order for every gauge to have some unique quality that Datadog can use to distinquish and aggregate
by.

Like histograms, gauges have a single ``set`` method that exhibits the same behavior, and have the same initial default
value behavior as histograms and counters.


Recorders
---------

Recorders encapsulate the functionality of creating and tracking metrics over an indefinite period of time and then
sending all accumulated metrics to the configured publishers on request. All recorders extend
``pymetrics.recorders.base.MetricsRecorder`` and provide methods for creating and publishing metrics. For more
information about these methods, see the
`reference documentation for MetricsRecorder <reference.html#pymetrics.recorders.base.MetricsRecorder>`_.


The No-Op Recorder
++++++++++++++++++

The no-op recorder ``pymetrics.recorders.noop.NonOperationalMetricsRecorder`` is useful for testing purposes or
defaulting your metrics to a recorder when no recorder was configured or provided in your documentation. This allows
you to record your metrics without having to constantly check if your recorder attribute is ``None`` or worrying about
configuring or mocking metrics during tests. In most cases, you'll want to just use the singleton instance
``pymetrics.recorders.noop.noop_metrics`` (this is especially useful as a default for function and method arguments).
This recorder creates and returns all the appropriate instruments but does not store or publish them in any way.

For more information about this class, see the
`reference documentation for NonOperationalMetricsRecorder <reference.html#pymetrics.recorders.noop.NonOperationalMetricsRecorder>`_.


The Default Recorder
++++++++++++++++++++

The ``pymetrics.recorders.default.DefaultMetricsRecorder`` is the work horse of PyMetrics. It takes a `Configuration`_
or, if not specified, attempts to find a configuration in Django settings (if Django is in use). It keeps track of
metrics as they are created, and then publishes those metrics to the configured publisher or publishers when one of the
publish methods is called. For more information about this class, see the
`reference documentation for DefaultMetricsRecorder <reference.html#pymetrics.recorders.default.DefaultMetricsRecorder>`_.


Decorators
++++++++++

Timers and counters support being recorded "around" the execution of methods and functions using the
``pymetrics.recorders.base.metric_decorator`` function. This function is used to create a timer or counter decorator
that you can then use to decorate your methods or functions. For detailed instructions about using this function and
the decorators it creates, see the
`reference documentation for metric_decorator <reference.html#pymetrics.recorders.base.metric_decorator>`_.


Publishers
----------

Up to this point, everything we have covered is generic and independent of the vendor you chose to consume and
aggregate your metrics. Publishers are the vendor-specific piece of the puzzle, and all publishers extend
``pymetrics.publishers.base.MetricsPublisher``. The ``pymetrics.publishers.base.NullPublisher`` is a lot like the
``NonOperationalMetricsRecorder``, but is perhaps more comparable to configuring a logger to log to ``/dev/null``, as
metrics will still be recorded and tracked, but then will just disappear into nowhere when published.

PyMetrics comes with several publishers, and the best way to learn about each is to see its reference documentation:

* `Python Logging publisher <reference.html#pymetrics.publishers.logging.LogPublisher>`_
* `Statsd <reference.html#pymetrics.publishers.statsd.StatsdPublisher>`_
* `Datadog via DogStatsd <reference.html#pymetrics.publishers.datadog.DogStatsdPublisher>`_
* `Abstract SQL publisher (must be extended) <reference.html#pymetrics.publishers.sql.SqlPublisher>`_
* `SQLite publisher <reference.html#pymetrics.publishers.sqlite.SqlitePublisher>`_


Configuration
-------------

PyMetrics has a standard configuration schema that uses `Conformity <https://github.com/eventbrite/conformity>`_ for
validation. When you configure PyMetrics, you pass a configuration dictionary matching this schema into the metrics
recorder you are using (currently only ``DefaultMetricsRecorder`` accepts a configuration) and then it gets converted
into a ``pymetrics.configuration.Configuration`` object. Alternatively, if you are using Django, you can define a
``METRICS_CONFIG`` setting matching the configuration schema and the recorder will discover this, validate it, and
convert it into a ``Configuration``. The recorder then uses the details in that configuration to publish the metrics
you record.

The `reference documentation for Configuration <reference.html#pymetrics.configuration.Configuration>`_ describes the
configuration schema in detail.

The metrics configuration will look something like this:

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

And then you can use it end-to-end with code like this:

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

    metrics.publish_all()  # metrics will be sent to the configured publisher(s), in this case DogStatsd
