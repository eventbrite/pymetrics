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
from pymetrics.publishers.null import NullMetricsPublisher


def test_null_publisher_creation():
    """Test creating a null publisher."""
    publisher = NullMetricsPublisher()
    assert publisher is not None


def test_null_publisher_publish():
    """Test publishing metrics to null publisher."""
    publisher = NullMetricsPublisher()

    metrics = [
        Counter("test_counter", initial_value=10),
        Gauge("test_gauge", initial_value=42),
        Histogram("test_histogram", initial_value=100),
        Timer("test_timer", initial_value=1.5),
    ]

    # This should not raise an exception
    publisher.publish(metrics)


def test_null_publisher_empty_metrics():
    """Test publishing empty metrics list."""
    publisher = NullMetricsPublisher()
    publisher.publish([])  # Should not raise an exception


def test_null_publisher_with_flush():
    """Test publishing with flush parameter."""
    publisher = NullMetricsPublisher()

    metrics = [
        Counter("test_counter", initial_value=10),
    ]

    # This should not raise an exception
    publisher.publish(metrics, flush=True)
    publisher.publish(metrics, flush=False)
