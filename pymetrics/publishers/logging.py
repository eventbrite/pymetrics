from __future__ import (
    absolute_import,
    unicode_literals,
)

import logging
from typing import (
    Any,
    Iterable,
    Union,
)

from pymetrics.instruments import Metric
from pymetrics.publishers.base import MetricsPublisher


class LoggingMetricsPublisher(MetricsPublisher):
    """
    A metrics publisher that logs metrics to a logger.
    """

    def __init__(self, log_name, log_level=logging.INFO):
        # type: (str, Union[int, str]) -> None
        """
        Initialize the publisher.

        :param log_name: The name of the logger to use
        :param log_level: The log level to use
        """
        self.logger = logging.getLogger(log_name)
        self.log_level = log_level

    def _get_str_value(self, value):
        # type: (Any) -> str
        """
        Convert a value to a string.

        :param value: The value to convert
        :return: The string representation
        """
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)

    def publish(self, metrics, flush=True):
        # type: (Iterable[Metric], bool) -> None
        """
        Log the metrics.

        :param metrics: The metrics to publish
        :param flush: Whether to flush (ignored)
        """
        if not metrics:
            return

        formatted_metrics = []
        for metric in metrics:
            formatted_metrics.append(" ".join((metric.name, self._get_str_value(metric.value))))

        self.logger.log(self.log_level, "Metrics: %s", "; ".join(formatted_metrics))
