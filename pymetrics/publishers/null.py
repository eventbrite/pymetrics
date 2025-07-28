from __future__ import (
    absolute_import,
    unicode_literals,
)

from typing import Iterable

from pymetrics.instruments import Metric
from pymetrics.publishers.base import MetricsPublisher


class NullMetricsPublisher(MetricsPublisher):
    """
    A null metrics publisher that does nothing.
    """

    def publish(self, metrics, flush=True):
        # type: (Iterable[Metric], bool) -> None
        """
        Do nothing with the metrics.

        :param metrics: The metrics to publish (ignored)
        :param flush: Whether to flush (ignored)
        """
        pass
