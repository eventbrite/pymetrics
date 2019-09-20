from __future__ import (
    absolute_import,
    unicode_literals,
)

import abc
import logging
from typing import (
    Any,
    Dict,
    Generator,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
)

import six

from pymetrics.instruments import (
    Counter,
    Gauge,
    Histogram,
    Metric,
    Timer,
)
from pymetrics.publishers.base import MetricsPublisher


__all__ = (
    'SqlPublisher',
)


class SqlPublisher(MetricsPublisher):
    """
    Abstract base class for publishers that publish to SQL databases of any type. Subclasses should implement all the
    backend-specific logic.
    """

    database_type = None  # type: Optional[six.text_type]
    """
    The name of the database backend type, used when logging errors.
    """

    exception_type = Exception  # type: Type[Exception]
    """
    The base class of all possible SQL exceptions this backend could raise, used for catching exceptions in order to
    log them.
    """

    @abc.abstractmethod
    def initialize_if_necessary(self):  # type: () -> None
        """Initialize the database connection, schema, etc., if necessary."""

    @abc.abstractmethod
    def execute_statement_multiple_times(self, statement, arguments):
        # type: (six.text_type, Generator[Tuple[Any, ...], None, None]) -> None
        """
        Execute a given statement multiple times (possibly prepared) using the given generator of argument tuples.

        :param statement: The SQL statement
        :param arguments: A generator of tuples of arguments, one tuple for each time the statement should be executed
        """

    def publish(self, metrics, error_logger=None, enable_meta_metrics=False):
        # type: (Iterable[Metric], six.text_type, bool) -> None
        if not metrics:
            return

        counters = []  # type: List[Counter]
        gauges = {}  # type: Dict[six.text_type, Gauge]
        timers = []  # type: List[Timer]
        histograms = []  # type: List[Histogram]

        for metric in metrics:
            if metric.value is None:
                continue

            if isinstance(metric, Counter):
                counters.append(metric)
            elif isinstance(metric, Gauge):
                gauges[metric.name] = metric
            elif isinstance(metric, Timer):
                timers.append(metric)
            elif isinstance(metric, Histogram):
                histograms.append(metric)

        self.initialize_if_necessary()

        # noinspection PyBroadException
        try:
            if counters:
                self.insert_counters(counters)
        except self.exception_type:
            if error_logger:
                logging.getLogger(error_logger).exception('Failed to send counters to {}'.format(self.database_type))

        # noinspection PyBroadException
        try:
            if gauges:
                self.insert_or_update_gauges(gauges.values())
        except self.exception_type:
            if error_logger:
                logging.getLogger(error_logger).exception('Failed to send gauges to {}'.format(self.database_type))

        # noinspection PyBroadException
        try:
            if timers:
                self.insert_timers(timers)
        except self.exception_type:
            if error_logger:
                logging.getLogger(error_logger).exception('Failed to send timers to {}'.format(self.database_type))

        # noinspection PyBroadException
        try:
            if histograms:
                self.insert_histograms(histograms)
        except self.exception_type:
            if error_logger:
                logging.getLogger(error_logger).exception('Failed to send histograms to {}'.format(self.database_type))

    def insert_counters(self, counters):  # type: (Iterable[Counter]) -> None
        # noinspection SqlNoDataSourceInspection,SqlResolve
        self.execute_statement_multiple_times(
            'INSERT INTO pymetrics_counters (metric_name, metric_value) VALUES (?, ?);',
            ((c.name, c.value) for c in counters),
        )

    def insert_or_update_gauges(self, gauges):  # type: (Iterable[Gauge]) -> None
        # noinspection SqlNoDataSourceInspection,SqlResolve
        self.execute_statement_multiple_times(
            'REPLACE INTO pymetrics_gauges (metric_name, metric_value) VALUES (?, ?);',
            ((g.name, g.value) for g in gauges),
        )

    def insert_timers(self, timers):  # type: (Iterable[Timer]) -> None
        # noinspection SqlNoDataSourceInspection,SqlResolve
        self.execute_statement_multiple_times(
            'INSERT INTO pymetrics_timers (metric_name, metric_value) VALUES (?, ?);',
            ((t.name, (float(t.value) / t.resolution)) for t in timers if t.value is not None),
        )

    def insert_histograms(self, histograms):  # type: (Iterable[Histogram]) -> None
        # noinspection SqlNoDataSourceInspection,SqlResolve
        self.execute_statement_multiple_times(
            'INSERT INTO pymetrics_histograms (metric_name, metric_value) VALUES (?, ?);',
            ((h.name, h.value) for h in histograms),
        )
