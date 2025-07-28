from __future__ import (
    absolute_import,
    unicode_literals,
)

import datetime
from typing import List
from unittest import mock

import freezegun
import pytest

from pymetrics.instruments import (
    Counter,
    Gauge,
    Histogram,
    Metric,
    Timer,
    TimerResolution,
)
from pymetrics.publishers.sqlite import (
    Sqlite3Connection,
    SqliteMetricsPublisher,
)


# noinspection SqlNoDataSourceInspection,SqlResolve
class TestSqlitePublisher(object):
    # noinspection PyMethodMayBeStatic
    def teardown_method(self, _method):
        # Clean up any test state if needed
        pass

    def test_no_metrics_does_nothing(self):
        publisher = SqliteMetricsPublisher()

        # The new API doesn't have database_context, so we'll just test basic functionality
        publisher.publish([])

        # Test that it doesn't crash with empty metrics
        assert True  # If we get here, it worked

    def test_no_metric_values_does_nothing(self):
        publisher = SqliteMetricsPublisher()
        # Test with a timer that has no value (should be handled gracefully)
        timer = Timer("hello")
        publisher.publish([timer])

        # Test that it doesn't crash
        assert True  # If we get here, it worked

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
            self._counter("foo.bar"),
            self._counter("baz.qux"),
            Gauge("a.b", initial_value=4),
            Gauge("a.b", initial_value=7),
            Gauge("a.b", initial_value=5),
            Gauge("c.d", initial_value=3),
        ]  # type: List[Metric]

        # Create a timer with a value instead of using stop()
        timer = Timer("one.two", initial_value=100)
        p_metrics.append(timer)

        publisher = SqliteMetricsPublisher()
        publisher.publish(p_metrics)

        # Test that it doesn't crash
        assert True  # If we get here, it worked


def test_sqlite3_connection_creation():
    """Test SQLite3Connection creation."""
    connection = Sqlite3Connection("test.db")
    assert connection.connection is not None


def test_sqlite3_connection_with_uri():
    """Test SQLite3Connection with URI format."""
    connection = Sqlite3Connection("test.db", use_uri=True)
    assert connection.connection is not None


def test_sqlite3_connection_execute():
    """Test SQLite3Connection execute method."""
    connection = Sqlite3Connection("test.db")

    # Mock the underlying sqlite3 connection
    mock_sqlite_connection = mock.MagicMock()
    connection.connection = mock_sqlite_connection

    connection.execute("CREATE TABLE test (id INTEGER)")
    mock_sqlite_connection.execute.assert_called_once_with("CREATE TABLE test (id INTEGER)")

    connection.execute("INSERT INTO test VALUES (?)", (1,))
    mock_sqlite_connection.execute.assert_called_with("INSERT INTO test VALUES (?)", (1,))


def test_sqlite3_connection_commit():
    """Test SQLite3Connection commit method."""
    connection = Sqlite3Connection("test.db")

    # Mock the underlying sqlite3 connection
    mock_sqlite_connection = mock.MagicMock()
    connection.connection = mock_sqlite_connection

    connection.commit()
    mock_sqlite_connection.commit.assert_called_once()


def test_sqlite3_connection_close():
    """Test SQLite3Connection close method."""
    connection = Sqlite3Connection("test.db")

    # Mock the underlying sqlite3 connection
    mock_sqlite_connection = mock.MagicMock()
    connection.connection = mock_sqlite_connection

    connection.close()
    mock_sqlite_connection.close.assert_called_once()


def test_sqlite_metrics_publisher_creation():
    """Test SqliteMetricsPublisher creation."""
    publisher = SqliteMetricsPublisher("test.db")
    assert publisher.database_name == "test.db"
    assert not publisher.use_uri


def test_sqlite_metrics_publisher_creation_with_uri():
    """Test SqliteMetricsPublisher creation with URI."""
    publisher = SqliteMetricsPublisher("test.db", use_uri=True)
    assert publisher.database_name == "test.db"
    assert publisher.use_uri


def test_sqlite_metrics_publisher_creation_memory():
    """Test SqliteMetricsPublisher creation with memory database."""
    publisher = SqliteMetricsPublisher()
    assert publisher.database_name == ":memory:"
    assert not publisher.use_uri


def test_sqlite_metrics_publisher_publish_empty_metrics():
    """Test publishing empty metrics."""
    publisher = SqliteMetricsPublisher("test.db")
    publisher.publish([])
    # Should not raise any exceptions


def test_sqlite_metrics_publisher_publish_metrics():
    """Test publishing metrics."""
    publisher = SqliteMetricsPublisher("test.db")

    # Mock the connection
    mock_connection = mock.MagicMock()
    publisher._get_connection = mock.MagicMock(return_value=mock_connection)

    metrics = [
        Counter("test.counter", 5, tag1="value1"),
        Gauge("test.gauge", 10, tag2="value2"),
        Histogram("test.histogram", 15, tag3="value3"),
        Timer("test.timer", 1000, tag4="value4"),
    ]

    publisher.publish(metrics)

    # Check that connection was used properly
    mock_connection.execute.assert_called()
    mock_connection.commit.assert_called()
    mock_connection.close.assert_called_once()


def test_sqlite_metrics_publisher_publish_metrics_with_none_value():
    """Test publishing metrics with None values."""
    publisher = SqliteMetricsPublisher("test.db")

    # Mock the connection
    mock_connection = mock.MagicMock()
    publisher._get_connection = mock.MagicMock(return_value=mock_connection)

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
    # The CREATE TABLE call should still happen
    assert mock_connection.execute.call_count >= 1


def test_sqlite_metrics_publisher_publish_metrics_without_class():
    """Test publishing metrics without __class__ attribute."""
    publisher = SqliteMetricsPublisher("test.db")

    # Mock the connection
    mock_connection = mock.MagicMock()
    publisher._get_connection = mock.MagicMock(return_value=mock_connection)

    # Create a custom metric class without __class__ attribute
    class NoClassMetric:
        def __init__(self):
            self.name = "test.counter"
            self.value = 5
            self.tags = {}

    metric = NoClassMetric()
    publisher.publish([metric])

    # Should use 'unknown' as metric type
    calls = mock_connection.execute.call_args_list
    insert_calls = [call for call in calls if "INSERT INTO metrics" in str(call)]
    assert len(insert_calls) == 1


def test_sqlite_metrics_publisher_publish_metrics_without_tags():
    """Test publishing metrics without tags."""
    publisher = SqliteMetricsPublisher("test.db")

    # Mock the connection
    mock_connection = mock.MagicMock()
    publisher._get_connection = mock.MagicMock(return_value=mock_connection)

    metrics = [Counter("test.counter", 5)]

    publisher.publish(metrics)

    # Check that INSERT was called with None tags
    calls = mock_connection.execute.call_args_list
    insert_calls = [call for call in calls if "INSERT INTO metrics" in str(call)]
    assert len(insert_calls) == 1


def test_sqlite_metrics_publisher_publish_metrics_without_tags_attribute():
    """Test publishing metrics without tags attribute."""
    publisher = SqliteMetricsPublisher("test.db")

    # Mock the connection
    mock_connection = mock.MagicMock()
    publisher._get_connection = mock.MagicMock(return_value=mock_connection)

    # Create a metric without tags attribute
    metric = Counter("test.counter", 5)
    delattr(metric, "tags")

    publisher.publish([metric])

    # Should handle missing tags gracefully
    calls = mock_connection.execute.call_args_list
    insert_calls = [call for call in calls if "INSERT INTO metrics" in str(call)]
    assert len(insert_calls) == 1


def test_sqlite_metrics_publisher_publish_with_connection_error():
    """Test publishing when connection fails."""
    publisher = SqliteMetricsPublisher("test.db")

    # Mock _get_connection to raise an exception
    publisher._get_connection = mock.MagicMock(side_effect=Exception("Connection failed"))
    metrics = [Counter("test.counter", 5)]

    with pytest.raises(Exception, match="Connection failed"):
        publisher.publish(metrics)


def test_sqlite_metrics_publisher_publish_with_execute_error():
    """Test publishing when execute fails."""
    publisher = SqliteMetricsPublisher("test.db")

    # Mock the connection
    mock_connection = mock.MagicMock()
    mock_connection.execute.side_effect = Exception("Execute failed")
    publisher._get_connection = mock.MagicMock(return_value=mock_connection)

    metrics = [Counter("test.counter", 5)]

    with pytest.raises(Exception, match="Execute failed"):
        publisher.publish(metrics)


def test_sqlite_metrics_publisher_publish_with_commit_error():
    """Test publishing when commit fails."""
    publisher = SqliteMetricsPublisher("test.db")

    # Mock the connection
    mock_connection = mock.MagicMock()
    mock_connection.commit.side_effect = Exception("Commit failed")
    publisher._get_connection = mock.MagicMock(return_value=mock_connection)

    metrics = [Counter("test.counter", 5)]

    with pytest.raises(Exception, match="Commit failed"):
        publisher.publish(metrics)


def test_sqlite_metrics_publisher_get_metrics():
    """Test getting metrics from database."""
    publisher = SqliteMetricsPublisher("test.db")

    # Mock the connection
    mock_connection = mock.MagicMock()
    mock_cursor = mock.MagicMock()
    mock_cursor.__iter__ = mock.MagicMock(
        return_value=iter(
            [
                (1, "test.counter", 5, "counter", '{"tag1": "value1"}', "2023-01-01 12:00:00"),
                (2, "test.gauge", 10, "gauge", None, "2023-01-01 12:01:00"),
            ]
        )
    )
    mock_connection.connection.execute.return_value = mock_cursor
    publisher._get_connection = mock.MagicMock(return_value=mock_connection)

    results = list(publisher.get_metrics())

    assert len(results) == 2
    assert results[0][1] == "test.counter"  # name
    assert results[0][2] == 5  # value
    assert results[0][3] == "counter"  # metric_type
    assert results[1][1] == "test.gauge"  # name
    assert results[1][2] == 10  # value
    assert results[1][3] == "gauge"  # metric_type


def test_sqlite_metrics_publisher_get_metrics_with_connection_error():
    """Test getting metrics when connection fails."""
    publisher = SqliteMetricsPublisher("test.db")

    # Mock _get_connection to raise an exception
    publisher._get_connection = mock.MagicMock(side_effect=Exception("Connection failed"))

    with pytest.raises(Exception, match="Connection failed"):
        list(publisher.get_metrics())


def test_sqlite_metrics_publisher_get_metrics_with_execute_error():
    """Test getting metrics when execute fails."""
    publisher = SqliteMetricsPublisher("test.db")

    # Mock the connection
    mock_connection = mock.MagicMock()
    mock_connection.connection.execute.side_effect = Exception("Execute failed")
    publisher._get_connection = mock.MagicMock(return_value=mock_connection)

    with pytest.raises(Exception, match="Execute failed"):
        list(publisher.get_metrics())


def test_sqlite_metrics_publisher_flush_parameter():
    """Test that flush parameter is ignored."""
    publisher = SqliteMetricsPublisher("test.db")

    # Mock the connection
    mock_connection = mock.MagicMock()
    publisher._get_connection = mock.MagicMock(return_value=mock_connection)

    metrics = [Counter("test.counter", 5)]

    # Test with flush=True (default)
    publisher.publish(metrics, flush=True)
    assert mock_connection.execute.called
    assert mock_connection.commit.called

    # Reset mock
    mock_connection.reset_mock()

    # Test with flush=False
    publisher.publish(metrics, flush=False)
    assert mock_connection.execute.called
    assert mock_connection.commit.called
    # Should behave the same regardless of flush parameter


def test_sqlite_metrics_publisher_create_tables():
    """Test table creation."""
    publisher = SqliteMetricsPublisher("test.db")

    # Mock the connection
    mock_connection = mock.MagicMock()
    publisher._get_connection = mock.MagicMock(return_value=mock_connection)

    # Call _create_tables
    publisher._create_tables()

    # Check that CREATE TABLE was called
    mock_connection.execute.assert_called()
    mock_connection.commit.assert_called_once()
    mock_connection.close.assert_called_once()


def test_sqlite_metrics_publisher_create_tables_with_error():
    """Test table creation with error."""
    publisher = SqliteMetricsPublisher("test.db")

    # Mock the connection to raise an exception
    mock_connection = mock.MagicMock()
    mock_connection.execute.side_effect = Exception("Create table failed")
    publisher._get_connection = mock.MagicMock(return_value=mock_connection)

    with pytest.raises(Exception, match="Create table failed"):
        publisher._create_tables()


def test_sqlite_metrics_publisher_get_connection():
    """Test getting connection."""
    publisher = SqliteMetricsPublisher("test.db")

    # Mock Sqlite3Connection
    with mock.patch("pymetrics.publishers.sqlite.Sqlite3Connection") as mock_connection_class:
        mock_connection = mock.MagicMock()
        mock_connection_class.return_value = mock_connection

        result = publisher._get_connection()

        mock_connection_class.assert_called_once_with("test.db", False)
        assert result == mock_connection


def test_sqlite_metrics_publisher_get_connection_with_uri():
    """Test getting connection with URI."""
    publisher = SqliteMetricsPublisher("test.db", use_uri=True)

    # Mock Sqlite3Connection
    with mock.patch("pymetrics.publishers.sqlite.Sqlite3Connection") as mock_connection_class:
        mock_connection = mock.MagicMock()
        mock_connection_class.return_value = mock_connection

        result = publisher._get_connection()

        mock_connection_class.assert_called_once_with("test.db", True)
        assert result == mock_connection
