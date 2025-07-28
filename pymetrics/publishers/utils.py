from __future__ import (
    absolute_import,
    unicode_literals,
)

from typing import Iterable

from pymetrics.instruments import Metric
from pymetrics.publishers.base import MetricsPublisher


__all__ = ("publish_metrics",)


def publish_metrics(metrics, configuration):
    # type: (Iterable[Metric], object) -> None
    """
    Publish metrics using the given configuration.

    :param metrics: The metrics to publish
    :param configuration: The configuration object
    """
    for publisher in configuration.publishers:
        publisher.publish(metrics)
