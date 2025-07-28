from __future__ import (
    absolute_import,
    unicode_literals,
)

import abc
from typing import Iterable

from pymetrics.instruments import Metric


__all__ = ("MetricsPublisher",)


class MetricsPublisher(abc.ABC):
    """
    Abstract base class for all metrics publishers.
    """

    @abc.abstractmethod
    def publish(self, metrics, flush=True):
        # type: (Iterable[Metric], bool) -> None
        """
        Publish the specified metrics.

        :param metrics: The metrics to publish
        :param flush: Whether to flush the publisher after publishing
        """
        raise NotImplementedError()
