from __future__ import (
    absolute_import,
    unicode_literals,
)

import errno
import logging
import socket
from typing import (
    Iterable,
    List,
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
    Timer,
    TimerResolution,
)
from pymetrics.publishers.base import MetricsPublisher


__all__ = (
    'StatsdPublisher',
)


IP_HEADER_BYTES = 20
UDP_HEADER_BYTES = 8
MAX_IPV4_PACKET_SIZE_BYTES = 65535
MAX_GIG_E_MTU_BYTES = 9000
MAX_FAST_E_MTU_BYTES = 1518
MAX_IPV4_PAYLOAD_SIZE_BYTES = MAX_IPV4_PACKET_SIZE_BYTES - IP_HEADER_BYTES - UDP_HEADER_BYTES
MAX_GIG_E_PAYLOAD_SIZE_BYTES = MAX_GIG_E_MTU_BYTES - IP_HEADER_BYTES - UDP_HEADER_BYTES
MAX_FAST_E_PAYLOAD_SIZE_BYTES = MAX_FAST_E_MTU_BYTES - IP_HEADER_BYTES - UDP_HEADER_BYTES


@fields.ClassConfigurationSchema.provider(fields.Dictionary(
    {
        'host': fields.UnicodeString(description='The host name or IP address on which the Statsd server is listening'),
        'port': fields.Integer(description='The port number on which the Statsd server is listening'),
        'maximum_packet_size': fields.Integer(
            description='The maximum packet size to send (packets will be fragmented above this limit), defaults to '
                        '65000 bytes.',
        ),
        'network_timeout': fields.Any(fields.Float(gt=0.0), fields.Integer(gt=0), description='The network timeout'),
    },
    optional_keys=('maximum_packet_size', 'network_timeout'),
))
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
        # type: (six.text_type, int, Union[int, float], int) -> None
        self.host = host
        self.port = port
        self.timeout = network_timeout
        self.maximum_packet_size = min(maximum_packet_size, self.MAXIMUM_PACKET_SIZE)

        self._metric_type_histogram = self.METRIC_TYPE_HISTOGRAM
        self._metric_type_timer = self.METRIC_TYPE_TIMER

    @staticmethod
    def _get_binary_value(string):  # type: (Union[six.text_type, six.binary_type]) -> six.binary_type
        if isinstance(string, six.text_type):
            return string.encode('utf-8')
        return string

    def get_formatted_metrics(self, metrics, enable_meta_metrics=False):
        # type: (Iterable[Metric], bool) -> List[six.binary_type]
        meta_timer = None
        if enable_meta_metrics:
            meta_timer = Timer('', resolution=TimerResolution.MICROSECONDS)

        formatted_metrics = []
        for metric in metrics:
            if metric.value is None:
                continue

            if isinstance(metric, Counter):
                type_label = self.METRIC_TYPE_COUNTER
            elif isinstance(metric, Gauge):
                type_label = self.METRIC_TYPE_GAUGE
            elif isinstance(metric, Timer):
                type_label = self._metric_type_timer
            elif isinstance(metric, Histogram):
                type_label = self._metric_type_histogram
            else:
                continue  # not possible unless a new metric type is added

            formatted_metrics.append(
                b'%s:%d|%s' % (self._get_binary_value(metric.name), metric.value, type_label)
            )

        if not formatted_metrics:
            return []

        if meta_timer:
            meta_timer.stop()
            formatted_metrics.insert(
                0,
                b'pymetrics.meta.publish.statsd.format_metrics:%d|%s' % (
                    cast(int, meta_timer.value),
                    self._metric_type_timer,
                )
            )

        return formatted_metrics

    def publish(self, metrics, error_logger=None, enable_meta_metrics=False):
        # type: (Iterable[Metric], six.text_type, bool) -> None
        if not metrics:
            return

        formatted_metrics = self.get_formatted_metrics(metrics, enable_meta_metrics)
        if not formatted_metrics:
            return

        # The maximum UDP packet size is 65,535 bytes. For localhost, that is also the maximum MTU. For now, all of our
        # metrics are sent over localhost, so we don't worry about the significantly-lower MTU realized over ethernet
        # networks. However, only Statsd allows this maximum size. DogStatsd caps the packet size at 8192. Even at the
        # maximum, we might still exceed that. The loss rate is incredibly tiny, but our analysis has shown that we do,
        # sometimes, lose metrics. So, for now, we chunk the values by the known limits to ensure we stay under those
        # limits.

        chunk = []  # type: List[six.binary_type]
        cumulative_length = 0
        for formatted_metric in formatted_metrics:
            metric_length = len(formatted_metric) + 1  # 1 is the length of a line terminator
            cumulative_length += metric_length

            if cumulative_length > self.maximum_packet_size:
                # This metric would put us over the packet size limit, so send the existing chunk and reset
                self._send_chunked_payload(b'\n'.join(chunk), len(chunk), error_logger, enable_meta_metrics)
                cumulative_length = metric_length
                chunk = []

            chunk.append(formatted_metric)

        if chunk:
            # We have unsent metrics left in the chunk, so send them
            self._send_chunked_payload(b'\n'.join(chunk), len(chunk), error_logger, enable_meta_metrics)

    def _send_chunked_payload(self, payload, number_of_metrics, error_logger=None, enable_meta_metrics=False):
        # type: (six.binary_type, int, six.text_type, bool) -> None
        meta_timer = None
        error = error_max_packet = False
        sock = None
        try:
            if enable_meta_metrics:
                meta_timer = Timer('', resolution=TimerResolution.MICROSECONDS)

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            sock.sendall(payload)
        except Exception as e:
            error = True
            if isinstance(e, socket.error) and e.errno == errno.EMSGSIZE:
                error_max_packet = True

            if error_logger:
                extra = {'data': {
                    'payload_length': len(payload),
                    'num_metrics': number_of_metrics,
                    'enable_meta_metrics': enable_meta_metrics,
                }}
                if error_max_packet:
                    logging.getLogger(error_logger).error(
                        'Failed to send metrics to statsd because UDP packet too big',
                        extra=extra,
                    )
                else:
                    logging.getLogger(error_logger).exception(
                        'Failed to send metrics to statsd {}:{}'.format(self.host, self.port),
                        extra=extra,
                    )
        finally:
            if sock:
                # noinspection PyBroadException
                try:
                    sock.close()
                except Exception:
                    pass
            if meta_timer:
                meta_timer.stop()

        if enable_meta_metrics:
            num_bytes = len(payload)  # TODO temporary; the length of the packet that we tried to send

            payload = b'pymetrics.meta.publish.statsd.send:1|%s' % self.METRIC_TYPE_COUNTER

            payload += b'\npymetrics.meta.publish.statsd.send.num_metrics:%d|%s' % (
                number_of_metrics,
                self._metric_type_histogram
            )

            if meta_timer:
                payload += b'\npymetrics.meta.publish.statsd.send.timer:%d|%s' % (
                    cast(int, meta_timer.value),
                    self._metric_type_timer,
                )

            if error:
                if error_max_packet:
                    payload += b'\npymetrics.meta.publish.statsd.send.error.max_packet:1|%s' % self.METRIC_TYPE_COUNTER
                else:
                    payload += b'\npymetrics.meta.publish.statsd.send.error.unknown:1|%s' % self.METRIC_TYPE_COUNTER

            # TODO The following three stats are temporary, to test out potential MTU problems noted above
            if num_bytes >= MAX_IPV4_PAYLOAD_SIZE_BYTES:
                payload += b'\npymetrics.meta.publish.statsd.send.exceeds_max_packet:1|%s' % self.METRIC_TYPE_COUNTER
            if num_bytes >= MAX_GIG_E_PAYLOAD_SIZE_BYTES:
                payload += b'\npymetrics.meta.publish.statsd.send.exceeds_max_gig_e:1|%s' % self.METRIC_TYPE_COUNTER
            if num_bytes >= MAX_FAST_E_PAYLOAD_SIZE_BYTES:
                payload += b'\npymetrics.meta.publish.statsd.send.exceeds_max_fast_e:1|%s' % self.METRIC_TYPE_COUNTER

            sock = None
            # noinspection PyBroadException
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(self.timeout)
                sock.connect((self.host, self.port))
                sock.sendall(payload)
            except Exception:
                if error_logger:
                    logging.getLogger(error_logger).exception(
                        'Failed to send meta metrics to statsd {}:{}'.format(self.host, self.port),
                    )
            finally:
                if sock:
                    # noinspection PyBroadException
                    try:
                        sock.close()
                    except Exception:
                        pass
