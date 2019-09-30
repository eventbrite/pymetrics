from __future__ import (
    absolute_import,
    unicode_literals,
)

import contextlib
import sqlite3
from typing import (
    Any,
    Generator,
    Optional,
    Tuple,
    cast,
)

from conformity import fields
import six

from pymetrics.publishers.sql import SqlPublisher


__all__ = (
    'SqlitePublisher',
)


class Sqlite3Connection(sqlite3.Connection):
    """
    An extension to the base connection. The base class is a pure C class on whose instances you can't call setattr.
    This extension enables the use of setattr on connection objects.
    """


@fields.ClassConfigurationSchema.provider(fields.Dictionary(
    {
        'database_name': fields.UnicodeString(description='The name of the Sqlite database to use'),
        'use_uri': fields.Boolean(
            description='Whether the database name should be treated as a URI (Python 3+ only)',
        ),
    },
    optional_keys=('database_name', 'use_uri'),
))
class SqlitePublisher(SqlPublisher):
    """
    A publisher that emits metrics to a Sqlite database file or in-memory database. Especially useful for use in tests
    where you need to actually evaluate your metrics.
    """

    database_type = 'Sqlite'
    exception_type = sqlite3.Error

    MEMORY_DATABASE_NAME = ':memory:'

    _memory_connection = None  # type: Optional[Sqlite3Connection]

    def __init__(self, database_name=MEMORY_DATABASE_NAME, use_uri=False):  # type: (six.text_type, bool) -> None
        if six.PY2 and use_uri:
            raise ValueError('Argument use_uri can only be used in Python 3 and higher')

        self.database_name = database_name
        self.use_uri = use_uri
        self.connection = None  # type: Optional[Sqlite3Connection]

    @staticmethod
    @contextlib.contextmanager
    def connection_context(connection):  # type: (sqlite3.Connection) -> Generator[sqlite3.Cursor, None, None]
        with connection:
            cursor = None
            try:
                cursor = connection.cursor()
                yield cursor
            finally:
                if cursor:
                    cursor.close()

    @contextlib.contextmanager
    def database_context(self):  # type: () -> Generator[sqlite3.Cursor, None, None]
        if not self.connection:
            raise ValueError('Call to database_context before database connection established')
        with self.connection_context(self.connection) as cursor:
            yield cursor

    def initialize_if_necessary(self):  # type: () -> None
        if not self.connection:
            self.connection = self.get_connection(self.database_name, self.use_uri)

        if not getattr(self.connection, '_pymetrics_initialized', None):
            with self.database_context() as cursor:
                # noinspection SqlNoDataSourceInspection,SqlResolve
                cursor.execute("SELECT name FROM sqlite_master WHERE name='pymetrics_counters';")
                needs_schema = cursor.fetchone() is None

            if needs_schema:
                with self.database_context() as cursor:
                    # noinspection SqlNoDataSourceInspection
                    cursor.executescript("""
CREATE TABLE pymetrics_counters (id INTEGER PRIMARY KEY, metric_name TEXT NOT NULL, metric_value INTEGER NOT NULL);

CREATE TABLE pymetrics_gauges (id INTEGER PRIMARY KEY, metric_name TEXT NOT NULL UNIQUE, metric_value INTEGER NOT NULL);

CREATE TABLE pymetrics_timers (id INTEGER PRIMARY KEY, metric_name TEXT NOT NULL, metric_value REAL NOT NULL);

CREATE TABLE pymetrics_histograms (id INTEGER PRIMARY KEY, metric_name TEXT NOT NULL, metric_value INTEGER NOT NULL);
""")

            setattr(self.connection, '_pymetrics_initialized', True)

    @classmethod
    def get_connection(cls, database_name=MEMORY_DATABASE_NAME, use_uri=False):
        # type: (six.text_type, bool) -> Sqlite3Connection
        if six.PY2 and use_uri:
            raise ValueError('Argument use_uri can only be used in Python 3 and higher')

        if database_name == cls.MEMORY_DATABASE_NAME and cls._memory_connection:
            # We only want a single in-memory connection per Python instance
            return cls._memory_connection

        kwargs = {}
        if use_uri:
            kwargs['uri'] = True

        connection = cast(Sqlite3Connection, sqlite3.connect(
            database_name,
            factory=Sqlite3Connection,
            timeout=0.1,
            isolation_level=None,
            check_same_thread=False,
            **kwargs
        ))
        connection.row_factory = sqlite3.Row

        if database_name == cls.MEMORY_DATABASE_NAME:
            cls._memory_connection = connection

        return connection

    def execute_statement_multiple_times(self, statement, arguments):
        # type: (six.text_type, Generator[Tuple[Any, ...], None, None]) -> None
        with self.database_context() as cursor:
            cursor.executemany(statement, arguments)

    @classmethod
    def clear_metrics_from_database(cls, connection):  # type: (sqlite3.Connection) -> None
        with cls.connection_context(connection) as cursor:
            # noinspection SqlNoDataSourceInspection,SqlResolve,SqlWithoutWhere
            cursor.executescript("""
DELETE FROM pymetrics_counters;
DELETE FROM pymetrics_gauges;
DELETE FROM pymetrics_timers;
DELETE FROM pymetrics_histograms;
""")
