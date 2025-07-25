import datetime
import pytest
from unittest import mock

from pymetrics.instruments import (
    Counter,
    Gauge,
    Histogram,
    Metric,
    Timer,
    TimerResolution,
)


def test_metric_abstract():
    """Test that Metric cannot be instantiated."""
    with pytest.raises(TypeError):
        Metric("test")


def test_metric_invalid_name():
    """Test that Metric rejects invalid names."""
    with pytest.raises(TypeError):
        Counter(123)  # Not a string


def test_metric_invalid_value():
    """Test that Metric rejects invalid values."""
    with pytest.raises(TypeError):
        Counter("test", "invalid")  # Not a number


def test_counter_basic():
    """Test basic counter functionality."""
    counter = Counter("test_counter")
    assert counter.value == 0
    counter.increment()
    assert counter.value == 1
    counter.increment(5)
    assert counter.value == 6


def test_counter_invalid_increment():
    """Test that counter rejects invalid increments."""
    counter = Counter("test_counter")
    with pytest.raises(ValueError):
        counter.increment(0)
    with pytest.raises(ValueError):
        counter.increment(-1)


def test_counter_reset():
    """Test counter reset functionality."""
    counter = Counter("test_counter", initial_value=10)
    assert counter.value == 10
    counter.reset(5)
    assert counter.value == 5
    counter.reset()
    assert counter.value == 10  # back to initial value


def test_counter_invalid_initial_value():
    """Test that counter rejects invalid initial values."""
    with pytest.raises(TypeError):
        Counter("test", -1)  # Negative value
    with pytest.raises(TypeError):
        Counter("test", 1.5)  # Float value


def test_counter_invalid_reset_value():
    """Test that counter rejects invalid reset values."""
    counter = Counter("test_counter")
    with pytest.raises(TypeError):
        counter.reset(-1)  # Negative value
    with pytest.raises(TypeError):
        counter.reset(1.5)  # Float value


def test_counter_record_over_function():
    """Test counter record_over_function method."""
    counter = Counter("test_counter")

    def test_func():
        return "success"

    result = counter.record_over_function(test_func)
    assert result == "success"
    assert counter.value == 1


def test_histogram_basic():
    """Test basic histogram functionality."""
    histogram = Histogram("test_histogram")
    assert histogram.value == 0
    histogram.set(10)
    assert histogram.value == 10
    histogram.set(5.7)
    assert histogram.value == 6  # Rounded


def test_histogram_reset():
    """Test histogram reset functionality."""
    histogram = Histogram("test_histogram", initial_value=5)
    assert histogram.value == 5
    histogram.set(10)
    assert histogram.value == 10
    histogram.set()  # Reset to initial
    assert histogram.value == 5


def test_histogram_with_tags():
    """Test histogram with tags."""
    histogram = Histogram("test_histogram", tag1="value1", tag2="value2")
    assert histogram.tags == {"tag1": "value1", "tag2": "value2"}


def test_gauge_basic():
    """Test basic gauge functionality."""
    gauge = Gauge("test_gauge")
    assert gauge.value == 0
    gauge.set(10)
    assert gauge.value == 10
    gauge.set(5)
    assert gauge.value == 5


def test_gauge_reset():
    """Test gauge reset functionality."""
    gauge = Gauge("test_gauge", initial_value=5)
    assert gauge.value == 5
    gauge.set(10)
    assert gauge.value == 10
    gauge.set()  # Reset to initial
    assert gauge.value == 5


def test_gauge_with_tags():
    """Test gauge with tags."""
    gauge = Gauge("test_gauge", tag1="value1", tag2="value2")
    assert gauge.tags == {"tag1": "value1", "tag2": "value2"}


def test_timer_basic():
    """Test basic timer functionality."""
    timer = Timer("test_timer")
    assert timer.value == 0
    timer.set(1000)  # 1 second in milliseconds
    assert timer.value == 1000000  # Timer multiplies by resolution


def test_timer_with_resolution():
    """Test timer with different resolutions."""
    timer = Timer("test_timer", resolution=TimerResolution.MICROSECONDS)
    timer.set(1000000)  # 1 second in microseconds
    assert timer.value == 1000000000000  # Timer multiplies by resolution


def test_timer_context_manager():
    """Test timer as context manager."""
    with Timer("test_timer") as timer:
        assert timer.name == "test_timer"
        # The timer might record 0 if execution is very fast
        assert timer.value >= 0


def test_timer_resolution():
    """Test timer resolution enum."""
    assert TimerResolution.MILLISECONDS == 1000
    assert TimerResolution.MICROSECONDS == 1000000
    assert TimerResolution.NANOSECONDS == 1000000000


def test_timer_start_stop():
    """Test timer start and stop methods."""
    timer = Timer("test_timer")
    timer.start()
    timer.stop()
    assert timer.value is not None
    assert timer.value >= 0


def test_timer_record_over_function():
    """Test timer record_over_function method."""
    timer = Timer("test_timer")

    def test_func():
        return "success"

    result = timer.record_over_function(test_func)
    assert result == "success"
    assert timer.value is not None
    assert timer.value >= 0


def test_metric_with_tags():
    """Test metric with tags."""
    counter = Counter("test_counter", tag1="value1", tag2="value2")
    assert counter.tags == {"tag1": "value1", "tag2": "value2"}


def test_metric_repr():
    """Test metric string representation."""
    counter = Counter("test_counter", initial_value=5)
    assert repr(counter) == 'Counter(name="test_counter", value=5)'


def test_metric_value_property():
    """Test metric value property."""
    counter = Counter("test_counter", initial_value=5)
    assert counter.value == 5  # Use integer value


def test_metric_record_over_function_unsupported():
    """Test that base Metric record_over_function raises TypeError."""
    # Create a subclass that doesn't override record_over_function
    class TestMetric(Metric):
        pass

    metric = TestMetric("test")
    with pytest.raises(TypeError):
        metric.record_over_function(lambda: None)


def test_timer_with_nanoseconds():
    """Test timer with nanoseconds resolution."""
    timer = Timer("test_timer", resolution=TimerResolution.NANOSECONDS)
    timer.set(1000000000)  # 1 second in nanoseconds
    assert timer.value == 1000000000000000000  # Timer multiplies by resolution


def test_timer_context_manager_exception():
    """Test timer context manager with exception."""
    timer = Timer("test_timer")
    try:
        with timer:
            raise ValueError("Test exception")
    except ValueError:
        pass
    # Timer should still have a value even with exception
    assert timer.value is not None


def test_metric_with_complex_tags():
    """Test metric with complex tag values."""
    counter = Counter("test_counter",
                     string_tag="value",
                     int_tag=42,
                     float_tag=3.14,
                     bool_tag=True,
                     none_tag=None)
    assert counter.tags["string_tag"] == "value"
    assert counter.tags["int_tag"] == 42
    assert counter.tags["float_tag"] == 3.14
    assert counter.tags["bool_tag"] is True
    assert counter.tags["none_tag"] is None
