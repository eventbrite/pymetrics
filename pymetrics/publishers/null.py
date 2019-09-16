from __future__ import (
    absolute_import,
    unicode_literals,
)

from conformity import fields

from pymetrics.publishers.base import MetricsPublisher


__all__ = (
    'NullPublisher',
)


@fields.ClassConfigurationSchema.provider(fields.Dictionary({}))
class NullPublisher(MetricsPublisher):
    def publish(self, metrics, error_logger=None, enable_meta_metrics=False):
        """Does nothing"""
