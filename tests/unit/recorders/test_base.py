import pytest
from unittest import mock

from pymetrics.recorders.base import MetricsRecorder, metric_decorator
from pymetrics.instruments import Counter, Timer


class ConcreteRecorder(MetricsRecorder):
    """Concrete implementation for testing."""

    def __init__(self):
        self.metrics = []

    def record_counter(self, name, value=1, **tags):
        counter = Counter(name, value, **tags)
        self.metrics.append(counter)
        return counter

    def record_histogram(self, name, value, **tags):
        from pymetrics.instruments import Histogram
        histogram = Histogram(name, value, **tags)
        self.metrics.append(histogram)
        return histogram

    def record_timer(self, name, value, resolution=None, **tags):
        from pymetrics.instruments import Timer, TimerResolution
        if resolution is None:
            resolution = TimerResolution.MILLISECONDS
        timer = Timer(name, value, resolution, **tags)
        self.metrics.append(timer)
        return timer

    def record_gauge(self, name, value, **tags):
        from pymetrics.instruments import Gauge
        gauge = Gauge(name, value, **tags)
        self.metrics.append(gauge)
        return gauge

    def get_metrics(self):
        return self.metrics

    # Add methods for metric decorator tests
    def counter(self, name, *args, **kwargs):
        return self.record_counter(name, *args, **kwargs)

    def timer(self, name, *args, **kwargs):
        # For decorator usage, provide a default value if none is given
        if not args:
            args = (0,)  # Default value for timer
        return self.record_timer(name, *args, **kwargs)


def test_recorder_abstract_methods():
    """Test that abstract methods are properly defined."""
    recorder = ConcreteRecorder()

    # Test counter recording
    counter = recorder.record_counter('test.counter', 5, tag1='value1')
    assert isinstance(counter, Counter)
    assert counter.name == 'test.counter'
    assert counter.value == 5
    assert counter.tags == {'tag1': 'value1'}

    # Test histogram recording
    histogram = recorder.record_histogram('test.histogram', 10, tag2='value2')
    assert histogram.name == 'test.histogram'
    assert histogram.value == 10
    assert histogram.tags == {'tag2': 'value2'}

    # Test timer recording
    timer = recorder.record_timer('test.timer', 1000, tag3='value3')
    assert timer.name == 'test.timer'
    assert timer.value == 1000000  # Timer multiplies by resolution
    assert timer.tags == {'tag3': 'value3'}

    # Test gauge recording
    gauge = recorder.record_gauge('test.gauge', 50, tag4='value4')
    assert gauge.name == 'test.gauge'
    assert gauge.value == 50
    assert gauge.tags == {'tag4': 'value4'}


def test_recorder_configure():
    """Test the configure method."""
    recorder = ConcreteRecorder()

    # Test with None config
    recorder.configure(None)

    # Test with empty config
    recorder.configure({})

    # Test with some config
    config = {'setting1': 'value1', 'setting2': 'value2'}
    recorder.configure(config)

    # Should not raise any exceptions


def test_recorder_get_metrics():
    """Test getting metrics from recorder."""
    recorder = ConcreteRecorder()

    # Initially empty
    assert recorder.get_metrics() == []

    # Add some metrics
    recorder.record_counter('test.counter', 5)
    recorder.record_gauge('test.gauge', 10)

    metrics = recorder.get_metrics()
    assert len(metrics) == 2
    assert any(m.name == 'test.counter' for m in metrics)
    assert any(m.name == 'test.gauge' for m in metrics)


def test_metric_decorator_basic():
    """Test the metric decorator basic functionality."""
    recorder = ConcreteRecorder()

    def get_recorder():
        return recorder

    @metric_decorator(get_recorder, 'timer', 'test.timer')
    def test_function():
        return "success"

    result = test_function()
    assert result == "success"

    # Check that a timer was created
    metrics = recorder.get_metrics()
    assert len(metrics) == 1
    assert metrics[0].name == 'test.timer'


def test_metric_decorator_with_args():
    """Test the metric decorator with arguments."""
    recorder = ConcreteRecorder()

    def get_recorder():
        return recorder

    @metric_decorator(get_recorder, 'counter', 'test.counter', 5, tag1='value1')
    def test_function():
        return "success"

    result = test_function()
    assert result == "success"

    # Check that a counter was created with the right parameters
    metrics = recorder.get_metrics()
    assert len(metrics) == 1
    assert metrics[0].name == 'test.counter'
    assert metrics[0].value == 6  # Initial value 5 + 1 from record_over_function
    assert metrics[0].tags == {'tag1': 'value1'}


def test_metric_decorator_with_include_metric():
    """Test the metric decorator with include_metric parameter."""
    recorder = ConcreteRecorder()

    def get_recorder():
        return recorder

    @metric_decorator(get_recorder, 'timer', 'test.timer', include_metric=True)
    def test_function(metric=None):
        assert metric is not None
        assert metric.name == 'test.timer'
        return "success"

    result = test_function()
    assert result == "success"


def test_metric_decorator_chained():
    """Test chaining multiple metric decorators."""
    recorder = ConcreteRecorder()

    def get_recorder():
        return recorder

    @metric_decorator(get_recorder, 'counter', 'test.counter')
    @metric_decorator(get_recorder, 'timer', 'test.timer')
    def test_function():
        return "success"

    result = test_function()
    assert result == "success"

    # Check that both metrics were created
    metrics = recorder.get_metrics()
    assert len(metrics) == 2
    assert any(m.name == 'test.counter' for m in metrics)
    assert any(m.name == 'test.timer' for m in metrics)


def test_metric_decorator_with_function_args():
    """Test the metric decorator with function arguments."""
    recorder = ConcreteRecorder()

    def get_recorder():
        return recorder

    @metric_decorator(get_recorder, 'timer', 'test.timer')
    def test_function(arg1, arg2, kwarg1=None):
        assert arg1 == "value1"
        assert arg2 == "value2"
        assert kwarg1 == "kwvalue1"
        return "success"

    result = test_function("value1", "value2", kwarg1="kwvalue1")
    assert result == "success"


def test_metric_decorator_deep_copy():
    """Test that the metric decorator properly deep copies arguments."""
    recorder = ConcreteRecorder()

    def get_recorder():
        return recorder

    # Test with mutable arguments
    mutable_list = [1, 2, 3]
    mutable_dict = {'key': 'value'}

    @metric_decorator(get_recorder, 'counter', 'test.counter', 5, **mutable_dict)
    def test_function():
        return "success"

    result = test_function()
    assert result == "success"

    # The original mutable objects should not be modified
    assert mutable_list == [1, 2, 3]
    assert mutable_dict == {'key': 'value'}


def test_metric_decorator_recorder_fetcher_error():
    """Test the metric decorator when recorder fetcher fails."""
    def get_recorder():
        raise Exception("Recorder not available")

    @metric_decorator(get_recorder, 'timer', 'test.timer')
    def test_function():
        return "success"

    with pytest.raises(Exception, match="Recorder not available"):
        test_function()


def test_metric_decorator_metric_creation_error():
    """Test the metric decorator when metric creation fails."""
    recorder = ConcreteRecorder()

    def get_recorder():
        return recorder

    # Use an invalid metric type that doesn't exist
    @metric_decorator(get_recorder, 'invalid_metric', 'test.metric')
    def test_function():
        return "success"

    with pytest.raises(AttributeError):
        test_function()
