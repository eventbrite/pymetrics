from __future__ import (
    absolute_import,
    unicode_literals,
)

import logging

import mock

from pymetrics.instruments import (
    Counter,
    Gauge,
    Histogram,
    Timer,
)
from pymetrics.publishers.logging import LogPublisher


@mock.patch('pymetrics.publishers.logging.logging.getLogger')
class TestLogPublisher(object):
    def test_no_metrics_does_nothing(self, mock_get_logger):
        publisher = LogPublisher(u'py_metrics', 'WARNING')
        mock_get_logger.assert_called_once_with(u'py_metrics')
        assert publisher.log_level == logging.WARNING

        publisher.publish([])
        assert mock_get_logger.return_value.log.call_count == 0

    def test_no_metric_values_does_nothing(self, mock_get_logger):
        publisher = LogPublisher(u'custom_metrics')
        mock_get_logger.assert_called_once_with(u'custom_metrics')
        assert publisher.log_level == logging.INFO

        publisher.publish([Timer(u'hello')])
        assert mock_get_logger.return_value.log.call_count == 0

    def test_metrics(self, mock_get_logger):
        publisher = LogPublisher(u'py_metrics', logging.DEBUG)
        assert publisher.log_level == logging.DEBUG
        mock_get_logger.assert_called_once_with(u'py_metrics')

        publisher.publish([
            Timer(u'hello.foo', initial_value=1),
            Counter(u'hello.bar', initial_value=2),
            Histogram(u'goodbye.baz', initial_value=3, neat_tag=u'production', other_tag=b'binary'),
            Gauge(u'goodbye.qux', initial_value=4),
        ])
        mock_get_logger.return_value.log.assert_called_once_with(
            logging.DEBUG,
            u'counters.hello.bar 2; '
            u'gauges.goodbye.qux 4; '
            u'histograms.goodbye.baz{neat_tag:production,other_tag:binary} 3; '
            u'timers.hello.foo 1',
        )
