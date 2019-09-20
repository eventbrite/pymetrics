from __future__ import (
    absolute_import,
    unicode_literals,
)

from typing import Type

import mock
import pytest

from pymetrics.instruments import (
    Counter,
    Gauge,
    Histogram,
    Timer,
    TimerResolution,
)
from pymetrics.publishers.sql import SqlPublisher


class E1(Exception):
    pass


class E2(Exception):
    pass


class MockPublisher(SqlPublisher):
    database_type = 'mock'

    def __init__(self, exception_type, to_raise):  # type: (Type[Exception], Type[Exception]) -> None
        self.exception_type = exception_type
        self.to_raise = to_raise
        self.initialize_called = False
        self.mock_execute = mock.MagicMock()

    def initialize_if_necessary(self):
        self.initialize_called = True

    def execute_statement_multiple_times(self, statement, arguments):
        self.mock_execute(statement, set(arguments))
        raise self.to_raise()


# noinspection SqlNoDataSourceInspection,SqlResolve
class TestSqlPublisher(object):
    def test_unrecognized_exception(self):
        metrics = [
            Counter('foo.count', initial_value=5),
            Gauge('bar.gauge', initial_value=3),
            Histogram('baz.hist', initial_value=6),
            Timer('qux.time', initial_value=1),
        ]

        publisher = MockPublisher(E2, E1)
        with pytest.raises(E1):
            publisher.publish(metrics)

    def test_recognized_exception_no_logger(self):
        metrics = [
            Counter('foo.count', initial_value=5),
            Gauge('bar.gauge', initial_value=3),
            Histogram('baz.hist', initial_value=6),
            Timer('qux.time1', initial_value=15),
            Timer('qux.time2', initial_value=723, resolution=TimerResolution.MICROSECONDS),
        ]

        publisher = MockPublisher(E2, E2)
        publisher.publish(metrics)
        publisher.mock_execute.assert_has_calls(
            [
                mock.call(
                    'INSERT INTO pymetrics_counters (metric_name, metric_value) VALUES (?, ?);',
                    {('foo.count', 5)},
                ),
                mock.call(
                    'REPLACE INTO pymetrics_gauges (metric_name, metric_value) VALUES (?, ?);',
                    {('bar.gauge', 3)},
                ),
                mock.call(
                    'INSERT INTO pymetrics_histograms (metric_name, metric_value) VALUES (?, ?);',
                    {('baz.hist', 6)},
                ),
                mock.call(
                    'INSERT INTO pymetrics_timers (metric_name, metric_value) VALUES (?, ?);',
                    {('qux.time1', 0.015), ('qux.time2', 0.000723)},
                ),
            ],
            any_order=True,
        )

    def test_recognized_exception_with_logger(self):
        metrics = [
            Counter('foo.count1', initial_value=1),
            Counter('foo.count2', initial_value=17),
            Gauge('bar.gauge1', initial_value=2),
            Gauge('bar.gauge2', initial_value=1),
            Histogram('baz.hist1', initial_value=33),
            Histogram('baz.hist2', initial_value=39),
            Timer('qux.time1', initial_value=21),
            Timer('qux.time2', initial_value=1837, resolution=TimerResolution.MICROSECONDS),
        ]

        publisher = MockPublisher(E1, E1)
        publisher.publish(metrics, error_logger='pymetrics')
        publisher.mock_execute.assert_has_calls(
            [
                mock.call(
                    'INSERT INTO pymetrics_counters (metric_name, metric_value) VALUES (?, ?);',
                    {('foo.count1', 1), ('foo.count2', 17)},
                ),
                mock.call(
                    'REPLACE INTO pymetrics_gauges (metric_name, metric_value) VALUES (?, ?);',
                    {('bar.gauge1', 2), ('bar.gauge2', 1)},
                ),
                mock.call(
                    'INSERT INTO pymetrics_histograms (metric_name, metric_value) VALUES (?, ?);',
                    {('baz.hist1', 33), ('baz.hist2', 39)},
                ),
                mock.call(
                    'INSERT INTO pymetrics_timers (metric_name, metric_value) VALUES (?, ?);',
                    {('qux.time1', 0.021), ('qux.time2', 0.001837)},
                ),
            ],
            any_order=True,
        )
