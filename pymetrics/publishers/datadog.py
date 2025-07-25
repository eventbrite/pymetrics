from typing import Dict, Iterable, List, Optional, Union

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
        host,  # type: str
        port,  # type: int
        network_timeout=0.5,  # type: Union[int, float]
        global_tags=None,  # type: Dict[str, Tag]
        extra_gauge_tags=None,  # type: Dict[str, Tag]
        use_distributions=False,  # type: bool
        maximum_packet_size=MAXIMUM_PACKET_SIZE,  # type: int
    ):
        """
        Initialize the publisher.

        :param host: The host name or IP address on which the Dogstatsd server is listening
        :param port: The port number on which the Dogstatsd server is listening
        :param network_timeout: The network timeout
        :param global_tags: Datadog tags to apply to all published metrics
        :param extra_gauge_tags: Extra datadog tags to apply to all published gauges
        :param use_distributions: Whether to publish histograms and timers as Datadog distributions
        :param maximum_packet_size: The maximum packet size to send
        """
        super(DogStatsdPublisher, self).__init__(host, port, network_timeout, maximum_packet_size)

        self.global_tags = global_tags or {}
        self.extra_gauge_tags = extra_gauge_tags or {}
        self.use_distributions = use_distributions

        if self.use_distributions:
            self._metric_type_histogram = self.METRIC_TYPE_DISTRIBUTION
            self._metric_type_timer = self.METRIC_TYPE_DISTRIBUTION

    @classmethod
    def _generate_tag_string(
        cls,
        tags,  # type: Optional[Dict[str, Tag]]
        existing_tags_string=b'',  # type: bytes
    ):
        # type: (...) -> bytes
        """
        Generate a tag string for Datadog.

        :param tags: The tags to format
        :param existing_tags_string: Existing tag string to append to
        :return: The formatted tag string
        """
        if not tags:
            return existing_tags_string

        tag_strings = []
        for tag, value in tags.items():
            if isinstance(value, int):
                tag_strings.append(f"{tag}:{value}")
            elif isinstance(value, float):
                tag_strings.append(f"{tag}:{value}")
            elif isinstance(value, bool):
                tag_strings.append(f"{tag}:{str(value).lower()}")
            else:
                # Convert to string
                tag_strings.append(f"{tag}:{value}")

        if tag_strings:
            tag_string = '|#{}'.format(','.join(tag_strings))
            return existing_tags_string + tag_string.encode('utf-8')

        return existing_tags_string

    def get_formatted_metrics(self, metrics, enable_meta_metrics=False):
        # type: (Iterable[Metric], bool) -> List[bytes]
        """
        Format metrics for DogStatsd.

        :param metrics: The metrics to format
        :param enable_meta_metrics: Whether to enable meta-metrics
        :return: A list of formatted metric bytes
        """
        formatted_metrics = []
        for metric in metrics:
            if metric.value is None:
                continue

            # Determine metric type
            if isinstance(metric, Counter):
                metric_type = self.METRIC_TYPE_COUNTER
            elif isinstance(metric, Gauge):
                metric_type = self.METRIC_TYPE_GAUGE
            elif isinstance(metric, (Histogram, Timer)):
                metric_type = self._metric_type_histogram
            else:
                continue

            # Build tags
            tags = {}
            tags.update(self.global_tags)
            if isinstance(metric, Gauge) and self.extra_gauge_tags:
                tags.update(self.extra_gauge_tags)
            if hasattr(metric, 'tags') and metric.tags:
                tags.update(metric.tags)

            # Format the metric
            metric_str = f"{metric.name}:{metric.value}|{metric_type.decode('utf-8')}"
            formatted_metric = metric_str.encode('utf-8')

            # Add tags if any
            if tags:
                tag_string = self._generate_tag_string(tags)
                formatted_metric += tag_string

            formatted_metrics.append(formatted_metric)

        return formatted_metrics
