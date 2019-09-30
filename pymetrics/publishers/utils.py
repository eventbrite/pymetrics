from __future__ import (
    absolute_import,
    unicode_literals,
)

from typing import Iterable

from pymetrics.configuration import Configuration
from pymetrics.instruments import Metric


__all__ = (
    'publish_metrics',
)


def publish_metrics(metrics, configuration):  # type: (Iterable[Metric], Configuration) -> None
    """
    Publish a set of metrics via the set of configured publishers.

    :param metrics: The metrics to publish
    :param configuration: The configuration object containing the configured publishers
    """

    for publisher in configuration.publishers:
        publisher.publish(metrics, configuration.error_logger_name, configuration.enable_meta_metrics)
