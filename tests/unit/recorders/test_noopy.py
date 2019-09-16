from __future__ import (
    absolute_import,
    unicode_literals,
)

from pymetrics.instruments import (
    Counter,
    Gauge,
    Histogram,
    Timer,
)
from pymetrics.recorders.noop import (
    NonOperationalMetricsRecorder,
    noop_metrics,
)


def test_noop_recorder():
    assert isinstance(noop_metrics, NonOperationalMetricsRecorder)

    assert isinstance(noop_metrics.counter('hello'), Counter)
    assert isinstance(noop_metrics.gauge('hello'), Gauge)
    assert isinstance(noop_metrics.histogram('hello'), Histogram)
    assert isinstance(noop_metrics.timer('hello'), Timer)

    assert noop_metrics.counter('hello') is not noop_metrics.counter('hello')
    assert noop_metrics.gauge('hello') is not noop_metrics.gauge('hello')
    assert noop_metrics.histogram('hello') is not noop_metrics.histogram('hello')
    assert noop_metrics.timer('hello') is not noop_metrics.timer('hello')

    noop_metrics.publish_all()
    noop_metrics.publish_if_full_or_old()
    noop_metrics.throttled_publish_all()
    noop_metrics.clear()
