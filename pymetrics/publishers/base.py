from __future__ import (
    absolute_import,
    unicode_literals,
)

import abc
from typing import Iterable

import six

from pymetrics.instruments import Metric


__all__ = (
    'MetricsPublisher',
)


@six.add_metaclass(abc.ABCMeta)
class MetricsPublisher(object):
    @abc.abstractmethod
    def publish(self, metrics, error_logger=None, enable_meta_metrics=False):
        # type: (Iterable[Metric], six.text_type, bool) -> None
        """
        Publish the provided metrics in the manner prescribed by the implementation's documentation.

        :param metrics: An iterable of all metrics that should be published
        :param error_logger: The name of the error logger that should be used if an error occurs (if no error logger
                             name is provided, errors will be suppressed)
        :param enable_meta_metrics: If `True`, metrics about the performance of this publisher will also be recorded
                                    (not all publishers will have meta-metrics to record).
        """
