import logging
import pytest
from unittest import mock

from pymetrics.configuration import Configuration, create_configuration
from pymetrics.recorders.base import MetricsRecorder
from pymetrics.publishers.base import MetricsPublisher
from pymetrics.instruments import Counter, Gauge, Histogram, Timer


class MockRecorder(MetricsRecorder):
    def record_counter(self, name, value=1, **tags):
        return None

    def record_histogram(self, name, value, **tags):
        return None

    def record_timer(self, name, value, resolution=None, **tags):
        return None

    def record_gauge(self, name, value, **tags):
        return None

    def get_metrics(self):
        return []


class MockPublisher(MetricsPublisher):
    def publish(self, metrics, flush=True):
        pass


def test_configuration_creation():
    recorder = MockRecorder()
    publisher = MockPublisher()
    config = Configuration(recorder=recorder, publishers=[publisher])
    assert config.recorder == recorder
    assert config.publishers == [publisher]


def test_configuration_with_error_logger():
    recorder = MockRecorder()
    config = Configuration(recorder=recorder, error_logger_name='test')
    assert config.error_logger_name == 'test'
    assert config._error_logger is not None


def test_configuration_without_error_logger():
    recorder = MockRecorder()
    config = Configuration(recorder=recorder)
    assert config.error_logger_name is None
    assert config._error_logger is None


def test_configuration_record_counter_success():
    recorder = MockRecorder()
    config = Configuration(recorder=recorder)
    config.record_counter('test.counter', 5, tag1='value1')
    # Should not raise any exceptions


def test_configuration_record_counter_with_error_logger():
    recorder = MockRecorder()
    config = Configuration(recorder=recorder, error_logger_name='test')

    # Mock the recorder to raise an exception
    with mock.patch.object(recorder, 'record_counter', side_effect=Exception('Test error')):
        # The logging is done directly in the configuration module
        config.record_counter('test.counter', 5)
        # Should not raise an exception


def test_configuration_record_counter_without_error_logger():
    recorder = MockRecorder()
    config = Configuration(recorder=recorder)

    # Mock the recorder to raise an exception
    with mock.patch.object(recorder, 'record_counter', side_effect=Exception('Test error')):
        # Should not raise an exception even when recorder fails
        config.record_counter('test.counter', 5)


def test_configuration_record_histogram_success():
    recorder = MockRecorder()
    config = Configuration(recorder=recorder)
    config.record_histogram('test.histogram', 10, tag1='value1')
    # Should not raise any exceptions


def test_configuration_record_histogram_with_error():
    recorder = MockRecorder()
    config = Configuration(recorder=recorder, error_logger_name='test')

    with mock.patch.object(recorder, 'record_histogram', side_effect=Exception('Test error')):
        # The logging is done directly in the configuration module
        config.record_histogram('test.histogram', 10)
        # Should not raise an exception


def test_configuration_record_timer_success():
    recorder = MockRecorder()
    config = Configuration(recorder=recorder)
    config.record_timer('test.timer', 100)
    # Should not raise any exceptions


def test_configuration_record_timer_with_resolution():
    recorder = MockRecorder()
    config = Configuration(recorder=recorder)
    from pymetrics.instruments import TimerResolution
    config.record_timer('test.timer', 100, resolution=TimerResolution.MICROSECONDS)
    # Should not raise any exceptions


def test_configuration_record_timer_with_error():
    recorder = MockRecorder()
    config = Configuration(recorder=recorder, error_logger_name='test')

    with mock.patch.object(recorder, 'record_timer', side_effect=Exception('Test error')):
        # The logging is done directly in the configuration module
        config.record_timer('test.timer', 100)
        # Should not raise an exception


def test_configuration_record_gauge_success():
    recorder = MockRecorder()
    config = Configuration(recorder=recorder)
    config.record_gauge('test.gauge', 50, tag1='value1')
    # Should not raise any exceptions


def test_configuration_record_gauge_with_error():
    recorder = MockRecorder()
    config = Configuration(recorder=recorder, error_logger_name='test')

    with mock.patch.object(recorder, 'record_gauge', side_effect=Exception('Test error')):
        # The logging is done directly in the configuration module
        config.record_gauge('test.gauge', 50)
        # Should not raise an exception


def test_configuration_publish_success():
    recorder = MockRecorder()
    publisher = MockPublisher()
    config = Configuration(recorder=recorder, publishers=[publisher])

    with mock.patch.object(recorder, 'get_metrics', return_value=[Counter('test')]):
        with mock.patch.object(publisher, 'publish') as mock_publish:
            config.publish()
            mock_publish.assert_called_once()


def test_configuration_publish_with_flush_false():
    recorder = MockRecorder()
    publisher = MockPublisher()
    config = Configuration(recorder=recorder, publishers=[publisher])

    with mock.patch.object(recorder, 'get_metrics', return_value=[Counter('test')]):
        with mock.patch.object(publisher, 'publish') as mock_publish:
            config.publish(flush=False)
            mock_publish.assert_called_once()


def test_configuration_publish_with_error():
    recorder = MockRecorder()
    publisher = MockPublisher()
    config = Configuration(recorder=recorder, publishers=[publisher], error_logger_name='test')

    with mock.patch.object(recorder, 'get_metrics', side_effect=Exception('Test error')):
        # The logging is done directly in the configuration module
        config.publish()
        # Should not raise an exception


def test_configuration_publish_with_publisher_error():
    recorder = MockRecorder()
    publisher = MockPublisher()
    config = Configuration(recorder=recorder, publishers=[publisher], error_logger_name='test')

    with mock.patch.object(recorder, 'get_metrics', return_value=[Counter('test')]):
        with mock.patch.object(publisher, 'publish', side_effect=Exception('Publisher error')):
            # The logging is done directly in the configuration module
            config.publish()
            # Should not raise an exception


def test_create_configuration_not_implemented():
    with pytest.raises(NotImplementedError):
        create_configuration({})
