from typing import Any, Generator, Iterable, Tuple

from pymetrics.instruments import Metric
from pymetrics.publishers.base import MetricsPublisher


class SqlMetricsPublisher(MetricsPublisher):
    """
    A metrics publisher that stores metrics in a SQL database.
    """

    def __init__(self, connection_factory, database_type=None):
        # type: (callable, str) -> None
        """
        Initialize the publisher.

        :param connection_factory: A factory function that returns a database connection
        :param database_type: The type of database (e.g., 'postgresql', 'mysql')
        """
        self.connection_factory = connection_factory
        self.database_type = database_type

    def publish(self, metrics, flush=True):
        # type: (Iterable[Metric], bool) -> None
        """
        Store metrics in the SQL database.

        :param metrics: The metrics to publish
        :param flush: Whether to flush (ignored)
        """
        if not metrics:
            return

        connection = self.connection_factory()
        try:
            for metric in metrics:
                if metric.value is None:
                    continue

                # Determine metric type
                if hasattr(metric, '__class__'):
                    metric_type = metric.__class__.__name__.lower()
                else:
                    metric_type = 'unknown'

                # Convert tags to string
                tags_str = None
                if hasattr(metric, 'tags') and metric.tags:
                    tags_str = str(metric.tags)

                # Insert the metric
                connection.execute(
                    'INSERT INTO metrics (name, value, metric_type, tags) VALUES (%s, %s, %s, %s)',
                    (metric.name, metric.value, metric_type, tags_str)
                )

            connection.commit()
        finally:
            connection.close()

    def get_metrics(self):
        # type: (str, Generator[Tuple[Any, ...], None, None]) -> None
        """
        Get all stored metrics.

        :param database_name: The database name
        :return: A generator of metric tuples
        """
        connection = self.connection_factory()
        try:
            cursor = connection.cursor()
            cursor.execute('SELECT * FROM metrics ORDER BY timestamp DESC')
            for row in cursor:
                yield row
        finally:
            connection.close()
