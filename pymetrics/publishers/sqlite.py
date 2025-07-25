import sqlite3
from typing import Any, Generator, Tuple

from pymetrics.instruments import Metric
from pymetrics.publishers.base import MetricsPublisher


MEMORY_DATABASE_NAME = ':memory:'


class Sqlite3Connection(object):
    """
    A wrapper around sqlite3.Connection to provide a consistent interface.
    """

    def __init__(self, database_name=MEMORY_DATABASE_NAME, use_uri=False):
        # type: (str, bool) -> None
        """
        Initialize the connection.

        :param database_name: The database name or path
        :param use_uri: Whether to use URI format
        """
        if use_uri:
            self.connection = sqlite3.connect(database_name, uri=True)
        else:
            self.connection = sqlite3.connect(database_name)

    def execute(self, sql, parameters=None):
        # type: (str, Tuple[Any, ...]) -> None
        """
        Execute a SQL statement.

        :param sql: The SQL statement
        :param parameters: The parameters for the statement
        """
        if parameters:
            self.connection.execute(sql, parameters)
        else:
            self.connection.execute(sql)

    def commit(self):
        """Commit the current transaction."""
        self.connection.commit()

    def close(self):
        """Close the connection."""
        self.connection.close()


class SqliteMetricsPublisher(MetricsPublisher):
    """
    A metrics publisher that stores metrics in SQLite.
    """

    def __init__(self, database_name=MEMORY_DATABASE_NAME, use_uri=False):
        # type: (str, bool) -> None
        """
        Initialize the publisher.

        :param database_name: The database name or path
        :param use_uri: Whether to use URI format
        """
        self.database_name = database_name
        self.use_uri = use_uri
        self._create_tables()

    def _create_tables(self):
        # type: () -> None
        """Create the necessary tables."""
        connection = self._get_connection()
        try:
            connection.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    value INTEGER NOT NULL,
                    metric_type TEXT NOT NULL,
                    tags TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            connection.commit()
        finally:
            connection.close()

    def _get_connection(self):
        # type: (str, bool) -> Sqlite3Connection
        """
        Get a database connection.

        :param database_name: The database name
        :param use_uri: Whether to use URI format
        :return: A database connection
        """
        return Sqlite3Connection(self.database_name, self.use_uri)

    def publish(self, metrics, flush=True):
        # type: (Iterable[Metric], bool) -> None
        if not metrics:
            return
        connection = self._get_connection()
        try:
            # Create tables if they don't exist
            connection.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    value INTEGER NOT NULL,
                    metric_type TEXT NOT NULL,
                    tags TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            connection.commit()

            for metric in metrics:
                if metric.value is None:
                    continue
                if hasattr(metric, '__class__'):
                    metric_type = metric.__class__.__name__.lower()
                else:
                    metric_type = 'unknown'
                tags_str = None
                if hasattr(metric, 'tags') and metric.tags:
                    tags_str = str(metric.tags)
                connection.execute(
                    'INSERT INTO metrics (name, value, metric_type, tags) VALUES (?, ?, ?, ?)',
                    (metric.name, metric.value, metric_type, tags_str)
                )
            connection.commit()
        finally:
            connection.close()

    def get_metrics(self):
        # type: (str, bool) -> Generator[Tuple[Any, ...], None, None]
        """
        Get all stored metrics.

        :param database_name: The database name
        :param use_uri: Whether to use URI format
        :return: A generator of metric tuples
        """
        connection = self._get_connection()
        try:
            cursor = connection.connection.execute('SELECT * FROM metrics ORDER BY timestamp DESC')
            for row in cursor:
                yield row
        finally:
            connection.close()
