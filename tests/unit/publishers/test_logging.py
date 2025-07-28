from __future__ import (
    absolute_import,
    unicode_literals,
)

import logging

from pymetrics.instruments import (
    Counter,
    Gauge,
    Histogram,
    Timer,
)
from pymetrics.publishers.logging import LoggingMetricsPublisher


def test_logging_publisher_creation():
    """Test creating a logging publisher."""
    publisher = LoggingMetricsPublisher("test_logger")
    assert publisher.logger.name == "test_logger"
    assert publisher.log_level == logging.INFO


def test_logging_publisher_with_custom_level():
    """Test creating a logging publisher with custom level."""
    publisher = LoggingMetricsPublisher("test_logger", logging.DEBUG)
    assert publisher.log_level == logging.DEBUG


def test_logging_publisher_publish():
    """Test publishing metrics to logger."""
    publisher = LoggingMetricsPublisher("test_logger")

    metrics = [
        Counter("test_counter", initial_value=10),
        Gauge("test_gauge", initial_value=42),
        Histogram("test_histogram", initial_value=100),
        Timer("test_timer", initial_value=1.5),
    ]

    # This should not raise an exception
    publisher.publish(metrics)


def test_logging_publisher_empty_metrics():
    """Test publishing empty metrics list."""
    publisher = LoggingMetricsPublisher("test_logger")
    publisher.publish([])  # Should not raise an exception


def test_logging_publisher_get_str_value():
    """Test the _get_str_value method."""
    publisher = LoggingMetricsPublisher("test_logger")

    # Test with string
    assert publisher._get_str_value("test") == "test"

    # Test with bytes
    assert publisher._get_str_value(b"test") == "test"

    # Test with number
    assert publisher._get_str_value(42) == "42"

    # Test with None
    assert publisher._get_str_value(None) == "None"
