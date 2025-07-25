from pymetrics.instruments import (
    Counter,
    Gauge,
    Histogram,
    Timer,
)
from pymetrics.recorders.noop import (
    NoopMetricsRecorder,
)


def test_noop_recorder():
    recorder = NoopMetricsRecorder()

    assert isinstance(recorder.record_counter('hello'), Counter)
    assert isinstance(recorder.record_gauge('hello', 5), Gauge)
    assert isinstance(recorder.record_histogram('hello', 10), Histogram)
    assert isinstance(recorder.record_timer('hello', 15), Timer)

    assert recorder.record_counter('hello') is not recorder.record_counter('hello')
    assert recorder.record_gauge('hello', 5) is not recorder.record_gauge('hello', 5)
    assert recorder.record_histogram('hello', 10) is not recorder.record_histogram('hello', 10)
    assert recorder.record_timer('hello', 15) is not recorder.record_timer('hello', 15)

    # Test get_metrics returns empty list
    assert recorder.get_metrics() == []
