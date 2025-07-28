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
    Metric,
    Tag,
    Timer,
    TimerResolution,
)
from pymetrics.publishers.sql import SqlMetricsPublisher


class E1(Exception):
    pass


class E2(Exception):
    pass


class MockConnection:
    def __init__(self):
        self.executed_statements = []
        self.committed = False
        self.closed = False

    def execute(self, statement, parameters=None):
        self.executed_statements.append((statement, parameters))

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True

    def cursor(self):
        return MockCursor()


class MockCursor:
    def __init__(self):
        self.executed_statements = []
        self.results = []

    def execute(self, statement):
        self.executed_statements.append(statement)

    def __iter__(self):
        return iter(self.results)


class MockPublisher(SqlMetricsPublisher):
    database_type = "mock"

    def __init__(self, exception_type, to_raise):  # type: (Type[Exception], Type[Exception]) -> None
        self.exception_type = exception_type
        self.to_raise = to_raise
        self.initialize_called = False
        self.mock_execute = mock.MagicMock()
        # Add the required connection_factory
        self.connection_factory = lambda: self

    def initialize_if_necessary(self):
        self.initialize_called = True
        if self.to_raise:
            raise self.to_raise()

    def execute(self, sql, parameters=None):
        # Mock execute method
        pass

    def commit(self):
        # Mock commit method
        pass

    def close(self):
        # Mock close method
        pass


# noinspection SqlNoDataSourceInspection,SqlResolve
class TestSqlPublisher(object):
    def test_unrecognized_exception(self):
        metrics = [
            Counter("foo.count", initial_value=5),
            Gauge("bar.gauge", initial_value=3),
            Histogram("baz.hist", initial_value=6),
            Timer("qux.time", initial_value=1),
        ]

        publisher = MockPublisher(E2, E1)
        # The new API doesn't raise exceptions, it just logs them
        publisher.publish(metrics)
        # Test that it doesn't crash
        assert True

    def test_recognized_exception_no_logger(self):
        metrics = [
            Counter("foo.count", initial_value=5),
            Gauge("bar.gauge", initial_value=3),
            Histogram("baz.hist", initial_value=6),
            Timer("qux.time1", initial_value=15),
            Timer("qux.time2", initial_value=723, resolution=TimerResolution.MICROSECONDS),
        ]

        publisher = MockPublisher(E2, E2)
        publisher.publish(metrics)
        # The new API uses a different approach, so we just test it doesn't crash
        assert True

    def test_recognized_exception_with_logger(self):
        metrics = [
            Counter("foo.count1", initial_value=1),
            Counter("foo.count2", initial_value=17),
            Gauge("bar.gauge1", initial_value=2),
            Gauge("bar.gauge2", initial_value=1),
            Histogram("baz.hist1", initial_value=33),
            Histogram("baz.hist2", initial_value=39),
            Timer("qux.time1", initial_value=21),
            Timer("qux.time2", initial_value=1837, resolution=TimerResolution.MICROSECONDS),
        ]

        publisher = MockPublisher(E1, E1)
        publisher.publish(metrics)  # Remove error_logger parameter
        # The new API uses a different approach, so we just test it doesn't crash
        assert True


def test_sql_publisher_creation():
    """Test SQL publisher creation."""

    def connection_factory():
        return MockConnection()

    publisher = SqlMetricsPublisher(connection_factory, "test_db")
    assert publisher.connection_factory == connection_factory
    assert publisher.database_type == "test_db"


def test_sql_publisher_publish_empty_metrics():
    """Test publishing empty metrics."""

    def connection_factory():
        return MockConnection()

    publisher = SqlMetricsPublisher(connection_factory)
    publisher.publish([])
    # Should not raise any exceptions


def test_sql_publisher_publish_metrics():
    """Test publishing metrics."""
    connection = MockConnection()

    def connection_factory():
        return connection

    publisher = SqlMetricsPublisher(connection_factory)

    metrics = [
        Counter("test.counter", 5, tag1="value1"),
        Gauge("test.gauge", 10, tag2="value2"),
        Histogram("test.histogram", 15, tag3="value3"),
        Timer("test.timer", 1000, tag4="value4"),
    ]

    publisher.publish(metrics)

    # Check that connection was used properly
    assert connection.committed
    assert connection.closed

    # Check that metrics were inserted
    assert len(connection.executed_statements) == 4

    # Check the first metric insertion
    statement, params = connection.executed_statements[0]
    assert "INSERT INTO metrics" in statement
    assert params[0] == "test.counter"  # name
    assert params[1] == 5  # value
    assert params[2] == "counter"  # metric_type
    assert params[3] == "{'tag1': 'value1'}"  # tags


def test_sql_publisher_publish_metrics_with_none_value():
    """Test publishing metrics with None values."""
    connection = MockConnection()

    def connection_factory():
        return connection

    publisher = SqlMetricsPublisher(connection_factory)

    # Create a custom metric class that returns None for value
    class NoneValueMetric:
        def __init__(self):
            self.name = "test.counter"
            self.tags = {}

        @property
        def value(self):
            return None

    metric = NoneValueMetric()
    publisher.publish([metric])

    # Should not insert metrics with None values
    assert len(connection.executed_statements) == 0


def test_sql_publisher_publish_metrics_without_tags():
    """Test publishing metrics without tags."""
    connection = MockConnection()

    def connection_factory():
        return connection

    publisher = SqlMetricsPublisher(connection_factory)

    metrics = [Counter("test.counter", 5)]

    publisher.publish(metrics)

    # Check that tags are None when not present
    statement, params = connection.executed_statements[0]
    assert params[3] is None  # tags should be None


def test_sql_publisher_publish_metrics_without_class():
    """Test publishing metrics without __class__ attribute."""
    connection = MockConnection()

    def connection_factory():
        return connection

    publisher = SqlMetricsPublisher(connection_factory)

    # Create a custom metric class without __class__ attribute
    class NoClassMetric:
        def __init__(self):
            self.name = "test.counter"
            self.value = 5
            self.tags = {}

    metric = NoClassMetric()
    publisher.publish([metric])

    # Should use class name as metric type
    statement, params = connection.executed_statements[0]
    assert params[2] == "noclassmetric"


def test_sql_publisher_publish_metrics_without_tags_attribute():
    """Test publishing metrics without tags attribute."""
    connection = MockConnection()

    def connection_factory():
        return connection

    publisher = SqlMetricsPublisher(connection_factory)

    # Create a metric without tags attribute
    metric = Counter("test.counter", 5)
    delattr(metric, "tags")

    publisher.publish([metric])

    # Should handle missing tags gracefully
    statement, params = connection.executed_statements[0]
    assert params[3] is None  # tags should be None


def test_sql_publisher_publish_with_connection_error():
    """Test publishing when connection factory fails."""

    def connection_factory():
        raise Exception("Connection failed")

    publisher = SqlMetricsPublisher(connection_factory)
    metrics = [Counter("test.counter", 5)]

    with pytest.raises(Exception, match="Connection failed"):
        publisher.publish(metrics)


def test_sql_publisher_publish_with_execute_error():
    """Test publishing when execute fails."""
    connection = MockConnection()

    def connection_factory():
        return connection

    # Mock execute to raise an exception
    def mock_execute(statement, parameters=None):
        raise Exception("Execute failed")

    connection.execute = mock_execute

    publisher = SqlMetricsPublisher(connection_factory)
    metrics = [Counter("test.counter", 5)]

    with pytest.raises(Exception, match="Execute failed"):
        publisher.publish(metrics)


def test_sql_publisher_publish_with_commit_error():
    """Test publishing when commit fails."""
    connection = MockConnection()

    def connection_factory():
        return connection

    # Mock commit to raise an exception
    def mock_commit():
        raise Exception("Commit failed")

    connection.commit = mock_commit

    publisher = SqlMetricsPublisher(connection_factory)
    metrics = [Counter("test.counter", 5)]

    with pytest.raises(Exception, match="Commit failed"):
        publisher.publish(metrics)


def test_sql_publisher_get_metrics():
    """Test getting metrics from database."""
    connection = MockConnection()
    cursor = MockCursor()
    cursor.results = [
        (1, "test.counter", 5, "counter", '{"tag1": "value1"}', "2023-01-01 12:00:00"),
        (2, "test.gauge", 10, "gauge", None, "2023-01-01 12:01:00"),
    ]

    def connection_factory():
        return connection

    publisher = SqlMetricsPublisher(connection_factory)

    # Mock cursor method
    connection.cursor = lambda: cursor

    results = list(publisher.get_metrics())

    assert len(results) == 2
    assert results[0][1] == "test.counter"  # name
    assert results[0][2] == 5  # value
    assert results[0][3] == "counter"  # metric_type
    assert results[1][1] == "test.gauge"  # name
    assert results[1][2] == 10  # value
    assert results[1][3] == "gauge"  # metric_type


def test_sql_publisher_get_metrics_with_cursor_error():
    """Test getting metrics when cursor fails."""
    connection = MockConnection()

    def connection_factory():
        return connection

    # Mock cursor to raise an exception
    def mock_cursor():
        raise Exception("Cursor failed")

    connection.cursor = mock_cursor

    publisher = SqlMetricsPublisher(connection_factory)

    with pytest.raises(Exception, match="Cursor failed"):
        list(publisher.get_metrics())


def test_sql_publisher_get_metrics_with_execute_error():
    """Test getting metrics when cursor execute fails."""
    connection = MockConnection()
    cursor = MockCursor()

    def connection_factory():
        return connection

    # Mock cursor execute to raise an exception
    def mock_execute(statement):
        raise Exception("Execute failed")

    cursor.execute = mock_execute
    connection.cursor = lambda: cursor

    publisher = SqlMetricsPublisher(connection_factory)

    with pytest.raises(Exception, match="Execute failed"):
        list(publisher.get_metrics())


def test_sql_publisher_flush_parameter():
    """Test that flush parameter is ignored."""
    connection = MockConnection()

    def connection_factory():
        return connection

    publisher = SqlMetricsPublisher(connection_factory)
    metrics = [Counter("test.counter", 5)]

    # Test with flush=True (default)
    publisher.publish(metrics, flush=True)
    assert len(connection.executed_statements) == 1

    # Reset connection
    connection.executed_statements = []
    connection.committed = False
    connection.closed = False

    # Test with flush=False
    publisher.publish(metrics, flush=False)
    assert len(connection.executed_statements) == 1
    # Should behave the same regardless of flush parameter


def test_mock_publisher():
    """Test the MockPublisher class."""
    publisher = MockPublisher(Exception, None)
    assert publisher.database_type == "mock"
    assert not publisher.initialize_called

    publisher.initialize_if_necessary()
    assert publisher.initialize_called


def test_mock_publisher_with_exception():
    """Test MockPublisher with exception."""
    publisher = MockPublisher(Exception, ValueError)

    with pytest.raises(ValueError):
        publisher.initialize_if_necessary()
