from __future__ import (
    absolute_import,
    unicode_literals,
)

from typing import (
    Dict,
    Iterable,
    List,
    Optional,
    Union,
    cast,
)

from conformity import fields
import six

from pymetrics.instruments import (
    Counter,
    Gauge,
    Histogram,
    Metric,
    Tag,
    Timer,
    TimerResolution,
)
from pymetrics.publishers.statsd import StatsdPublisher


__all__ = (
    'DogStatsdPublisher',
)


_datadog_tags_value_type = fields.Nullable(
    fields.Any(fields.UnicodeString(), fields.ByteString(), fields.Integer(), fields.Float(), fields.Boolean()),
)


@fields.ClassConfigurationSchema.provider(fields.Dictionary(
    {
        'host': fields.UnicodeString(
            description='The host name or IP address on which the Dogstatsd server is listening',
        ),
        'port': fields.Integer(description='The port number on which the Dogstatsd server is listening'),
        'maximum_packet_size': fields.Integer(
            description='The maximum packet size to send (packets will be fragmented above this limit), defaults to '
                        '8000 bytes.',
        ),
        'network_timeout': fields.Any(fields.Float(gt=0.0), fields.Integer(gt=0), description='The network timeout'),
        'global_tags': fields.SchemalessDictionary(
            key_type=fields.UnicodeString(),
            value_type=_datadog_tags_value_type,
            description='Datadog tags to apply to all published metrics.',
        ),
        'extra_gauge_tags': fields.SchemalessDictionary(
            key_type=fields.UnicodeString(),
            value_type=_datadog_tags_value_type,
            description='Extra datadog tags, in addition to `global_tags` if applicable, to apply to all published '
                        'gauges. This is necessary when multiple processes are simultaneously publishing gauges with '
                        'the same name and you need to create charts or monitors that sum the values of all of these '
                        'gauges across all processes (because Datadog does not support identical distributed gauge '
                        'names+tags and will eliminate duplicates).',
        ),
        'use_distributions': fields.Boolean(
            description='Whether to publish histograms and timers as Datadog distributions. For more information '
                        'about Datadog distributions, see https://docs.datadoghq.com/graphing/metrics/distributions/.'
                        'Defaults to `False`.',
        ),
    },
    optional_keys=('maximum_packet_size', 'network_timeout', 'global_tags', 'extra_gauge_tags', 'use_distributions'),
))
class DogStatsdPublisher(StatsdPublisher):
    """
    A special version of the Statsd publisher than understands the DataDog extensions to the Statsd protocol
    (histograms, distributions, and tags).

    For DogStatsd metric type suffixes, see https://docs.datadoghq.com/developers/dogstatsd/#datagram-format.
    """

    METRIC_TYPE_HISTOGRAM = b'h'
    METRIC_TYPE_DISTRIBUTION = b'd'

    MAXIMUM_PACKET_SIZE = 8000
    """
    Maximum size of the DogStatsd packet buffer, which is used as the maximum and default maximum packet size for this
    publisher (can be configured lower to account for lower MTU). See https://github.com/DataDog/dd-agent/issues/2638
    and https://github.com/DataDog/dd-agent/blob/e805a9a2022803d832cf7f7d8fa8895fd686945c/dogstatsd.py#L367.
    """

    def __init__(
        self,
        host,  # type: six.text_type
        port,  # type: int
        network_timeout=0.5,  # type: Union[int, float]
        global_tags=None,  # type: Dict[six.text_type, Tag]
        extra_gauge_tags=None,  # type: Dict[six.text_type, Tag]
        use_distributions=False,  # type: bool
        maximum_packet_size=MAXIMUM_PACKET_SIZE,  # type: int
    ):
        # type: (...) -> None
        super(DogStatsdPublisher, self).__init__(host, port, network_timeout, maximum_packet_size)

        if global_tags and not isinstance(global_tags, dict):
            raise ValueError('Global tags must be dicts')
        if extra_gauge_tags and not isinstance(extra_gauge_tags, dict):
            raise ValueError('Extra gauge tags must be dicts')

        self._global_tags_string = self._generate_tag_string(global_tags)
        self._global_gauge_tags_string = self._generate_tag_string(extra_gauge_tags, self._global_tags_string)

        if use_distributions:
            self._metric_type_histogram = self.METRIC_TYPE_DISTRIBUTION
            self._metric_type_timer = self.METRIC_TYPE_DISTRIBUTION

    @classmethod
    def _generate_tag_string(
        cls,
        tags,  # type: Optional[Dict[six.text_type, Tag]]
        existing_tags_string=b'',  # type: six.binary_type
    ):
        # type: (...) -> six.binary_type
        if not tags:
            return existing_tags_string

        if existing_tags_string:
            tags_string = existing_tags_string
            first = False
        else:
            tags_string = b'|#'
            first = True

        for tag, value in six.iteritems(tags):
            value_string = b''
            if value is not None:
                if isinstance(value, six.integer_types):
                    value_string = b':%d' % value
                elif isinstance(value, float):
                    value_string = (b':%f' % value).rstrip(b'0')
                else:
                    value_string = b':%s' % cls._get_binary_value(value)
            if first:
                tags_string += b'%s%s' % (cls._get_binary_value(tag), value_string)
                first = False
            else:
                tags_string += b',%s%s' % (cls._get_binary_value(tag), value_string)

        return tags_string

    def get_formatted_metrics(self, metrics, enable_meta_metrics=False):
        # type: (Iterable[Metric], bool) -> List[six.binary_type]
        meta_timer = None
        if enable_meta_metrics:
            meta_timer = Timer('', resolution=TimerResolution.MICROSECONDS)

        formatted_metrics = []
        for metric in metrics:
            if metric.value is None:
                continue

            existing_tags_string = self._global_tags_string

            if isinstance(metric, Counter):
                type_label = self.METRIC_TYPE_COUNTER
            elif isinstance(metric, Gauge):
                type_label = self.METRIC_TYPE_GAUGE
                existing_tags_string = self._global_gauge_tags_string
            elif isinstance(metric, Timer):
                type_label = self._metric_type_timer
            elif isinstance(metric, Histogram):
                type_label = self._metric_type_histogram
            else:
                continue

            metric_tags_string = self._generate_tag_string(metric.tags, existing_tags_string)

            formatted_metrics.append(
                b'%s:%d|%s%s' % (self._get_binary_value(metric.name), metric.value, type_label, metric_tags_string)
            )

        if not formatted_metrics:
            return []

        if meta_timer:
            meta_timer.stop()
            formatted_metrics.insert(
                0,
                b'pymetrics.meta.publish.statsd.format_metrics:%d|%s%s' % (
                    cast(int, meta_timer.value),
                    self._metric_type_timer,
                    self._global_tags_string,
                ),
            )

        return formatted_metrics
