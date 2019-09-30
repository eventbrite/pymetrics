from __future__ import (
    absolute_import,
    unicode_literals,
)

import logging
from typing import (
    Any,
    Iterable,
    Union,
    cast,
)

from conformity import fields
from conformity.fields.logging import PythonLogLevel
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
    'LogPublisher',
)


@fields.ClassConfigurationSchema.provider(fields.Dictionary(
    {
        'log_name': fields.UnicodeString(description='The name of the logger to which to publish metrics'),
        'log_level': fields.Any(
            fields.Constant(10, 20, 30, 40, 50),
            PythonLogLevel(),
            description='The log level (name or int) for publishing metrics, defaults to logging.INFO',
        ),
    },
    optional_keys=('log_level', ),
))
class LogPublisher(MetricsPublisher):
    def __init__(self, log_name, log_level=logging.INFO):  # type: (six.text_type, Union[int, six.text_type]) -> None
        self.log_name = log_name
        self.logger = logging.getLogger(self.log_name)

        if isinstance(log_level, int):
            self.log_level = log_level
        else:
            # getLevelName is a misnomer. It returns the name if you pass an int and the int if you pass a name.
            self.log_level = cast(int, logging.getLevelName(log_level))

    @staticmethod
    def _get_str_value(value):  # type: (Any) -> six.text_type
        if isinstance(value, six.binary_type):
            return value.decode('utf-8')
        return six.text_type(value)

    def publish(self, metrics, error_logger=None, enable_meta_metrics=False):
        # type: (Iterable[Metric], six.text_type, bool) -> None
        if not metrics:
            return

        formatted_metrics = []

        for metric in sorted(metrics, key=lambda x: '.'.join((str(type(x)), x.name))):
            if metric.value is None:
                continue

            name = metric.name
            if isinstance(metric, Counter):
                name = '.'.join(('counters', name))
            elif isinstance(metric, Gauge):
                name = '.'.join(('gauges', name))
            elif isinstance(metric, Timer):
                name = '.'.join(('timers', name))
            elif isinstance(metric, Histogram):
                name = '.'.join(('histograms', name))

            if getattr(metric, 'tags', None):
                name += '{{{}}}'.format(
                    ','.join(
                        '{}:{}'.format(k, self._get_str_value(v) if v is not None else '[no value]')
                        for k, v in sorted(metric.tags.items(), key=lambda x: x[0])
                    ),
                )

            formatted_metrics.append(' '.join((name, six.text_type(metric.value))))

        if not formatted_metrics:
            return

        self.logger.log(self.log_level, '; '.join(formatted_metrics))
