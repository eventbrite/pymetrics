from __future__ import (
    absolute_import,
    unicode_literals,
)

import datetime
from typing import List

import freezegun
import pytest
import six

from pymetrics.instruments import (
    Counter,
    Gauge,
    Histogram,
    Metric,
    Timer,
    TimerResolution,
)
from pymetrics.publishers.sqlite import SqlitePublisher


# noinspection SqlNoDataSourceInspection,SqlResolve
class TestSqlitePublisher(object):
    # noinspection PyMethodMayBeStatic
    def teardown_method(self, _method):
        SqlitePublisher.clear_metrics_from_database(SqlitePublisher.get_connection())

    def test_no_metrics_does_nothing(self):
        if six.PY2:
            with pytest.raises(ValueError):
                SqlitePublisher(database_name='file:///does/not/matter', use_uri=True)

            with pytest.raises(ValueError):
                SqlitePublisher.get_connection(database_name='file:///does/not/matter', use_uri=True)

        publisher = SqlitePublisher()

        with pytest.raises(ValueError):
            with publisher.database_context():  # call before initialization
                print('Should never get here')

        publisher.initialize_if_necessary()
        publisher.publish([])

        connection = SqlitePublisher.get_connection()
        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_counters;")
            assert len(list(cursor.fetchall())) == 0
        finally:
            cursor.close()
        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_gauges;")
            assert len(list(cursor.fetchall())) == 0
        finally:
            cursor.close()
        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_histograms;")
            assert len(list(cursor.fetchall())) == 0
        finally:
            cursor.close()
        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_timers;")
            assert len(list(cursor.fetchall())) == 0
        finally:
            cursor.close()

    def test_no_metric_values_does_nothing(self):
        publisher = SqlitePublisher()
        publisher.publish([Timer(u'hello')])

        connection = SqlitePublisher.get_connection()
        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_counters;")
            assert len(list(cursor.fetchall())) == 0
        finally:
            cursor.close()
        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_gauges;")
            assert len(list(cursor.fetchall())) == 0
        finally:
            cursor.close()
        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_histograms;")
            assert len(list(cursor.fetchall())) == 0
        finally:
            cursor.close()
        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_timers;")
            assert len(list(cursor.fetchall())) == 0
        finally:
            cursor.close()

    @staticmethod
    def _counter(*args, **kwargs):
        c = Counter(*args, **kwargs)
        c.increment()
        return c

    @staticmethod
    def _milliseconds(m):
        return datetime.timedelta(milliseconds=m)

    def test_metrics(self):
        p_metrics = [
            self._counter('foo.bar'),
            self._counter('baz.qux'),
            Gauge('a.b', initial_value=4),
            Gauge('a.b', initial_value=7),
            Gauge('a.b', initial_value=5),
            Gauge('c.d', initial_value=3),
        ]  # type: List[Metric]

        timer = Timer('one.two')
        timer.stop()
        p_metrics.append(timer)

        with freezegun.freeze_time() as frozen_time:
            timer = Timer('one.two')
            frozen_time.tick(self._milliseconds(50))
            timer.stop()
            p_metrics.append(timer)

            timer = Timer('one.two')
            frozen_time.tick(self._milliseconds(30))
            timer.stop()
            p_metrics.append(timer)

            timer = Timer('three.four')
            frozen_time.tick(self._milliseconds(10))
            timer.stop()
            p_metrics.append(timer)

        p_metrics.extend([
            Histogram('h.foo', initial_value=1),
            Histogram('h.foo', initial_value=3),
            Histogram('h.foo', initial_value=2),
            Histogram('h.bar', initial_value=77),
        ])

        publisher = SqlitePublisher()
        publisher.publish(p_metrics)

        connection = SqlitePublisher.get_connection()
        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_counters WHERE metric_name = 'foo.bar';")
            metrics = list(cursor.fetchall())

            assert len(metrics) == 1
            assert metrics[0][str('metric_name')] == 'foo.bar'
            assert metrics[0][str('metric_value')] == 1
        finally:
            cursor.close()

        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_counters WHERE metric_name = 'baz.qux';")
            metrics = list(cursor.fetchall())

            assert len(metrics) == 1
            assert metrics[0][str('metric_name')] == 'baz.qux'
            assert metrics[0][str('metric_value')] == 1
        finally:
            cursor.close()

        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_gauges WHERE metric_name = 'a.b';")
            metrics = list(cursor.fetchall())

            assert len(metrics) == 1
            assert metrics[0][str('metric_name')] == 'a.b'
            assert metrics[0][str('metric_value')] == 5
        finally:
            cursor.close()

        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_gauges WHERE metric_name = 'c.d';")
            metrics = list(cursor.fetchall())

            assert len(metrics) == 1
            assert metrics[0][str('metric_name')] == 'c.d'
            assert metrics[0][str('metric_value')] == 3
        finally:
            cursor.close()

        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_timers WHERE metric_name = 'one.two';")
            metrics = list(cursor.fetchall())

            assert len(metrics) == 3
            assert metrics[0][str('metric_name')] == 'one.two'
            assert metrics[0][str('metric_value')] < 0.001
            assert metrics[1][str('metric_name')] == 'one.two'
            assert 0.05 <= metrics[1][str('metric_value')] < 0.06
            assert metrics[2][str('metric_name')] == 'one.two'
            assert 0.03 <= metrics[2][str('metric_value')] < 0.04
        finally:
            cursor.close()

        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_timers WHERE metric_name = 'three.four';")
            metrics = list(cursor.fetchall())

            assert len(metrics) == 1
            assert metrics[0][str('metric_name')] == 'three.four'
            assert 0.01 <= metrics[0][str('metric_value')] < 0.02
        finally:
            cursor.close()

        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_histograms WHERE metric_name = 'h.foo';")
            metrics = list(cursor.fetchall())

            assert len(metrics) == 3
            assert metrics[0][str('metric_name')] == 'h.foo'
            assert metrics[0][str('metric_value')] == 1
            assert metrics[1][str('metric_name')] == 'h.foo'
            assert metrics[1][str('metric_value')] == 3
            assert metrics[2][str('metric_name')] == 'h.foo'
            assert metrics[2][str('metric_value')] == 2
        finally:
            cursor.close()

        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_histograms WHERE metric_name = 'h.bar';")
            metrics = list(cursor.fetchall())

            assert len(metrics) == 1
            assert metrics[0][str('metric_name')] == 'h.bar'
            assert metrics[0][str('metric_value')] == 77
        finally:
            cursor.close()

        p_metrics = [
            self._counter('foo.bar'),
            Gauge('a.b', initial_value=22),
            Gauge('c.d', initial_value=11),
        ]

        with freezegun.freeze_time() as frozen_time:
            timer = Timer('three.four', resolution=TimerResolution.MICROSECONDS)
            frozen_time.tick(self._milliseconds(20))
            timer.stop()
            p_metrics.append(timer)

        p_metrics.append(Histogram('h.foo', initial_value=8))

        publisher = SqlitePublisher()
        publisher.initialize_if_necessary()
        publisher.publish(p_metrics)

        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_counters WHERE metric_name = 'foo.bar';")
            metrics = list(cursor.fetchall())

            assert len(metrics) == 2
            assert metrics[0][str('metric_name')] == 'foo.bar'
            assert metrics[0][str('metric_value')] == 1
            assert metrics[1][str('metric_name')] == 'foo.bar'
            assert metrics[1][str('metric_value')] == 1
        finally:
            cursor.close()

        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_counters WHERE metric_name = 'baz.qux';")
            metrics = list(cursor.fetchall())

            assert len(metrics) == 1
            assert metrics[0][str('metric_name')] == 'baz.qux'
            assert metrics[0][str('metric_value')] == 1
        finally:
            cursor.close()

        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_gauges WHERE metric_name = 'a.b';")
            metrics = list(cursor.fetchall())

            assert len(metrics) == 1
            assert metrics[0][str('metric_name')] == 'a.b'
            assert metrics[0][str('metric_value')] == 22
        finally:
            cursor.close()

        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_gauges WHERE metric_name = 'c.d';")
            metrics = list(cursor.fetchall())

            assert len(metrics) == 1
            assert metrics[0][str('metric_name')] == 'c.d'
            assert metrics[0][str('metric_value')] == 11
        finally:
            cursor.close()

        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_timers WHERE metric_name = 'one.two';")
            metrics = list(cursor.fetchall())

            assert len(metrics) == 3
            assert metrics[0][str('metric_name')] == 'one.two'
            assert metrics[0][str('metric_value')] < 0.001
            assert metrics[1][str('metric_name')] == 'one.two'
            assert 0.05 <= metrics[1][str('metric_value')] < 0.06
            assert metrics[2][str('metric_name')] == 'one.two'
            assert 0.03 <= metrics[2][str('metric_value')] < 0.04
        finally:
            cursor.close()

        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_timers WHERE metric_name = 'three.four';")
            metrics = list(cursor.fetchall())

            assert len(metrics) == 2
            assert metrics[0][str('metric_name')] == 'three.four'
            assert 0.01 <= metrics[0][str('metric_value')] < 0.02
            assert metrics[1][str('metric_name')] == 'three.four'
            assert 0.02 <= metrics[1][str('metric_value')] < 0.03
        finally:
            cursor.close()

        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_histograms WHERE metric_name = 'h.foo';")
            metrics = list(cursor.fetchall())

            assert len(metrics) == 4
            assert metrics[0][str('metric_name')] == 'h.foo'
            assert metrics[0][str('metric_value')] == 1
            assert metrics[1][str('metric_name')] == 'h.foo'
            assert metrics[1][str('metric_value')] == 3
            assert metrics[2][str('metric_name')] == 'h.foo'
            assert metrics[2][str('metric_value')] == 2
            assert metrics[3][str('metric_name')] == 'h.foo'
            assert metrics[3][str('metric_value')] == 8
        finally:
            cursor.close()

        cursor = connection.cursor()
        try:
            # noinspection PyTypeChecker
            cursor.execute("SELECT * FROM pymetrics_histograms WHERE metric_name = 'h.bar';")
            metrics = list(cursor.fetchall())

            assert len(metrics) == 1
            assert metrics[0][str('metric_name')] == 'h.bar'
            assert metrics[0][str('metric_value')] == 77
        finally:
            cursor.close()
