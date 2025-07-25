import errno
import logging
import socket
from typing import Iterable, List, Union

from pymetrics.instruments import (
    Counter,
    Gauge,
    Histogram,
    Metric,
    Timer,
    TimerResolution,
)
from pymetrics.publishers.base import MetricsPublisher


IP_HEADER_BYTES = 20
UDP_HEADER_BYTES = 8
MAX_IPV4_PACKET_SIZE_BYTES = 65535
MAX_GIG_E_MTU_BYTES = 9000
MAX_FAST_E_MTU_BYTES = 1518
MAX_IPV4_PAYLOAD_SIZE_BYTES = MAX_IPV4_PACKET_SIZE_BYTES - IP_HEADER_BYTES - UDP_HEADER_BYTES
MAX_GIG_E_PAYLOAD_SIZE_BYTES = MAX_GIG_E_MTU_BYTES - IP_HEADER_BYTES - UDP_HEADER_BYTES
MAX_FAST_E_PAYLOAD_SIZE_BYTES = MAX_FAST_E_MTU_BYTES - IP_HEADER_BYTES - UDP_HEADER_BYTES


class StatsdPublisher(MetricsPublisher):
    """
    A publisher that emits UDP metrics packets to a Statsd consumer over a network connection.

    For Statsd metric type suffixes, see https://github.com/etsy/statsd/blob/master/docs/metric_types.md.
    """

    METRIC_TYPE_COUNTER = b'c'
    METRIC_TYPE_GAUGE = b'g'
    METRIC_TYPE_HISTOGRAM = b'ms'
    METRIC_TYPE_TIMER = b'ms'

    MAXIMUM_PACKET_SIZE = 65000
    """
    Maximum size of a localhost UDP packet, which is used as the maximum maximum and default maximum packet size for
    this publisher (can be configured lower to account for lower MTU).
    """

    def __init__(self, host, port, network_timeout=0.5, maximum_packet_size=MAXIMUM_PACKET_SIZE):
        # type: (str, int, Union[int, float], int) -> None
        """
        Initialize the publisher.

        :param host: The host name or IP address on which the Statsd server is listening
        :param port: The port number on which the Statsd server is listening
        :param network_timeout: The network timeout
        :param maximum_packet_size: The maximum packet size to send
        """
        self.host = host
        self.port = port
        self.timeout = network_timeout
        self.maximum_packet_size = min(maximum_packet_size, self.MAXIMUM_PACKET_SIZE)

        self._metric_type_histogram = self.METRIC_TYPE_HISTOGRAM
        self._metric_type_timer = self.METRIC_TYPE_TIMER

    @staticmethod
    def _get_binary_value(string):
        # type: (Union[str, bytes]) -> bytes
        """
        Convert a string to bytes.

        :param string: The string to convert
        :return: The bytes representation
        """
        if isinstance(string, str):
            return string.encode('utf-8')
        return string

    def get_formatted_metrics(self, metrics, enable_meta_metrics=False):
        # type: (Iterable[Metric], bool) -> List[bytes]
        """
        Format metrics for Statsd.

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

            # Format the metric
            metric_str = f"{metric.name}:{metric.value}|{metric_type.decode('utf-8')}"
            formatted_metrics.append(metric_str.encode('utf-8'))

        return formatted_metrics

    def publish(self, metrics, flush=True):
        # type: (Iterable[Metric], bool) -> None
        """
        Publish metrics to Statsd.

        :param metrics: The metrics to publish
        :param flush: Whether to flush (ignored)
        """
        if not metrics:
            return

        formatted_metrics = self.get_formatted_metrics(metrics)
        if not formatted_metrics:
            return

        # Join all metrics with newlines
        payload = b'\n'.join(formatted_metrics)

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(self.timeout)
                sock.sendto(payload, (self.host, self.port))
        except (socket.error, OSError) as e:
            logging.error('Failed to send metrics to Statsd: %s', e)

    def _send_chunked_payload(self, payload, number_of_metrics, error_logger=None, enable_meta_metrics=False):
        # type: (bytes, int, str, bool) -> None
        """
        Send a chunked payload to Statsd.

        :param payload: The payload to send
        :param number_of_metrics: The number of metrics in the payload
        :param error_logger: The error logger name
        :param enable_meta_metrics: Whether to enable meta-metrics
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(self.timeout)
                sock.sendto(payload, (self.host, self.port))
        except (socket.error, OSError) as e:
            if error_logger:
                logging.getLogger(error_logger).error(
                    'Failed to send %d metrics to Statsd: %s', number_of_metrics, e
                )
