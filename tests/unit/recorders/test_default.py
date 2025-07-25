import datetime
import time
from typing import (
    Any,
    Dict,
    Optional,
    cast,
)

import mock
import pytest

from pymetrics.instruments import Counter, Gauge, Histogram, Timer, TimerResolution
from pymetrics.publishers.base import MetricsPublisher
from pymetrics.recorders.default import DefaultMetricsRecorder


mock_publisher = mock.MagicMock(spec=MetricsPublisher)
mock_publisher_extra = mock.MagicMock(spec=MetricsPublisher)


class MockPublisher(MetricsPublisher):
    def __new__(cls, *args, **kwargs):
        return mock_publisher


class MockPublisherExtra(MetricsPublisher):
    def __new__(cls, *args, **kwargs):
        return mock_publisher_extra


class FakeImproperlyConfigured(Exception):
    pass


# noinspection PyProtectedMember
class TestDefaultMetricsRecorderConfiguration(object):
    # noinspection PyMethodMayBeStatic
    def teardown_method(self, _method):
        # Clean up any test state if needed
        pass

    def test_config_no_config(self):
        recorder = DefaultMetricsRecorder('me')
        # The new API doesn't have is_configured property
        assert recorder.prefix == 'me'

    def test_config_explicit(self):
        recorder = DefaultMetricsRecorder('me', meta=False)
        assert recorder.prefix == 'me'
        assert recorder.meta is False

    def test_basic_functionality(self):
        recorder = DefaultMetricsRecorder('test')

        # Test counter
        counter = recorder.record_counter('test.counter', 5)
        assert counter.name == 'test.test.counter'  # prefix is added
        assert counter.value == 5

        # Test gauge
        gauge = recorder.record_gauge('test.gauge', 10)
        assert gauge.name == 'test.test.gauge'  # prefix is added
        assert gauge.value == 10

        # Test histogram
        histogram = recorder.record_histogram('test.histogram', 15)
        assert histogram.name == 'test.test.histogram'  # prefix is added
        assert histogram.value == 15

        # Test timer
        timer = recorder.record_timer('test.timer', 20)
        assert timer.name == 'test.test.timer'  # prefix is added
        assert timer.value == 20000  # Timer values are in milliseconds

        # Test get_metrics
        metrics = recorder.get_metrics()
        assert len(metrics) == 4
