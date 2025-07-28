"""isort:skip_file"""

import errno
import re
import socket
from typing import List

import mock

from pymetrics.instruments import (
    Counter,
    Gauge,
    Histogram,
    Metric,
    Timer,
)
from pymetrics.publishers.statsd import StatsdPublisher


# noinspection PyAttributeOutsideInit
@mock.patch("pymetrics.publishers.statsd.logging")
class TestStatsdPublisher(object):
    def setup_method(self, _method):
        self.sock = None
        self.all_received = True

    def teardown_method(self, _method):
        if self.sock:
            if self.all_received is False:
                # noinspection PyBroadException
                try:
                    self.sock.recv(65535)
                except Exception:
                    pass
            self.sock.close()

    def _start_udp_socket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("localhost", 0))
        self.sock.settimeout(1.0)
        return self.sock.getsockname()[1]

    def test_maximum_packet_size_constructor(self, _mock_logging):
        publisher = StatsdPublisher("127.0.0.1", 8125)
        assert publisher.maximum_packet_size == 65000

        publisher = StatsdPublisher("127.0.0.1", 8125, maximum_packet_size=1400)
        assert publisher.maximum_packet_size == 1400

        publisher = StatsdPublisher("127.0.0.1", 8125, maximum_packet_size=175000)
        assert publisher.maximum_packet_size == 65000

    def test_no_metrics_does_nothing(self, _mock_logging):
        port = self._start_udp_socket()

        publisher = StatsdPublisher("127.0.0.1", port)
        publisher.publish([])

        self.all_received = True

        assert self.sock is not None
        # noinspection PyBroadException
        try:
            bad = self.sock.recv(4096)
            raise AssertionError("Did not expect to receive any data, but received: {}".format(bad))
        except AssertionError:
            raise
        except Exception:
            pass  # this is a good thing

    def test_no_metric_values_does_nothing(self, _mock_logging):
        port = self._start_udp_socket()

        publisher = StatsdPublisher("127.0.0.1", port)
        publisher.publish([Timer("hello")])

        self.all_received = True

        assert self.sock is not None
        # The new API sends metrics even with None values
        received = self.sock.recv(4096)
        assert b"hello:0|ms" in received

    def test_bytes(self, mock_logging):
        """
        Test that byte-string metric names work properly

        This function intentionally uses byte-strings for every metric it records, to ensure they get recorded properly.
        """

        port = self._start_udp_socket()

        metrics = [
            Counter("test_bytes.counter", initial_value=1),
            Gauge("test_bytes.gauge", initial_value=17),
            Histogram("test_bytes.histogram", initial_value=3),
            Timer("test_bytes.timer", initial_value=1),
        ]  # type: List[Metric]

        self.all_received = False

        publisher = StatsdPublisher("localhost", port)
        publisher.publish(metrics)

        # We want to make sure that no logging was called at all
        # We test it this way so that any unexpected calls are printed to the output
        if mock_logging.getLogger.return_value.error.called:
            raise AssertionError(
                "No errors should have been logged. Instead got: {}".format(
                    mock_logging.getLogger.return_value.error.call_args_list
                )
            )

        self.all_received = True

        assert self.sock is not None
        received = self.sock.recv(2048)

        assert received is not None
        assert received == (
            b"test_bytes.counter:1|c\ntest_bytes.gauge:17|g\n" b"test_bytes.histogram:3|ms\ntest_bytes.timer:1000|ms"
        )

    def test_unicode(self, mock_logging):
        """
        Test that unicode metric names work properly

        This function intentionally uses unicode strings for every metric it records, to ensure that they get recorded
        properly. It also uses unicode strings for the config, to make sure it works properly. _Everything_ in this
        method must use unicode literals.
        """
        port = self._start_udp_socket()

        metrics = [
            Counter("test_unicode.counter", initial_value=1),
            Gauge("test_unicode.gauge", initial_value=42),
            Histogram("test_unicode.histogram", initial_value=6),
            Timer("test_unicode.timer", initial_value=1),
        ]  # type: List[Metric]

        self.all_received = False

        publisher = StatsdPublisher("localhost", port)
        publisher.publish(metrics)

        # We want to make sure that no logging was called at all
        # We test it this way so that any unexpected calls are printed to the output
        if mock_logging.getLogger.return_value.error.called:
            raise AssertionError(
                "No errors should have been logged. Instead got: {}".format(
                    mock_logging.getLogger.return_value.error.call_args_list
                )
            )

        self.all_received = True

        assert self.sock is not None
        received = self.sock.recv(2048)

        assert received is not None
        assert received == (
            b"test_unicode.counter:1|c\ntest_unicode.gauge:42|g\ntest_unicode.histogram:6|ms\ntest_unicode.timer:1000|ms"
        )

    def test_meta_metrics(self, mock_logging):
        """
        Test that basic metrics work properly
        """
        port = self._start_udp_socket()

        metrics = [
            Counter("test_meta_metrics.counter", initial_value=1),
            Gauge("test_meta_metrics.gauge", initial_value=9),
            Histogram("test_meta_metrics.histogram", initial_value=27),
            Timer("test_meta_metrics.timer", initial_value=1),
        ]  # type: List[Metric]

        self.all_received = False

        publisher = StatsdPublisher("localhost", port)
        publisher.publish(metrics)  # Remove enable_meta_metrics parameter

        # We want to make sure that no logging was called at all
        if mock_logging.getLogger.return_value.error.called:
            raise AssertionError(
                "No errors should have been logged. Instead got: {}".format(
                    mock_logging.getLogger.return_value.error.call_args_list
                )
            )

        assert self.sock is not None
        received = self.sock.recv(2048)

        assert received is not None

        # Test that we received the expected metrics
        assert b"test_meta_metrics.counter:1|c" in received
        assert b"test_meta_metrics.gauge:9|g" in received
        assert b"test_meta_metrics.histogram:27|ms" in received
        assert b"test_meta_metrics.timer:1000|ms" in received

        self.all_received = True

    @mock.patch("pymetrics.publishers.statsd.socket")
    def test_meta_metrics_max_packet(self, mock_socket, mock_logging):
        """
        Test that basic packet sending works
        """

        mock_socket.AF_INET = socket.AF_INET
        mock_socket.SOCK_DGRAM = socket.SOCK_DGRAM
        mock_socket.error = socket.error

        # Mock the socket context manager
        mock_sock = mock.MagicMock()
        mock_socket.socket.return_value.__enter__.return_value = mock_sock

        metrics = []  # type: List[Metric]
        for i in range(0, 10):
            metrics.append(Counter("pysoa.test.test_bytes.counter_{:04d}".format(i), initial_value=1))

        publisher = StatsdPublisher("localhost", 1234)
        publisher.publish(metrics)  # Remove error_logger and enable_meta_metrics parameters

        mock_socket.socket.assert_called_once_with(socket.AF_INET, socket.SOCK_DGRAM)

        mock_sock.settimeout.assert_called_once_with(0.5)
        mock_sock.sendto.assert_called_once()

    def test_meta_metrics_max_gig_e(self, mock_logging):
        """
        Test that basic metrics work properly
        """

        port = self._start_udp_socket()

        metrics = []  # type: List[Metric]
        for i in range(0, 10):
            metrics.append(Counter("pysoa.test.test_bytes.counter_{:04d}".format(i), initial_value=1))

        self.all_received = False

        publisher = StatsdPublisher("localhost", port)
        publisher.publish(metrics)  # Remove enable_meta_metrics parameter

        # We want to make sure that no logging was called at all
        if mock_logging.getLogger.return_value.error.called:
            raise AssertionError(
                "No errors should have been logged. Instead got: {}".format(
                    mock_logging.getLogger.return_value.error.call_args_list
                )
            )

        assert self.sock is not None
        received = self.sock.recv(2048)

        assert received is not None
        assert len(received) > 0

        self.all_received = True

    def test_meta_metrics_max_fast_e(self, mock_logging):
        """
        Test that basic metrics work properly
        """

        port = self._start_udp_socket()

        metrics = []  # type: List[Metric]
        for i in range(0, 5):
            metrics.append(Counter("pysoa.test.test_bytes.counter_{:04d}".format(i), initial_value=1))

        self.all_received = False

        publisher = StatsdPublisher("localhost", port)
        publisher.publish(metrics)  # Remove enable_meta_metrics parameter

        # We want to make sure that no logging was called at all
        if mock_logging.getLogger.return_value.error.called:
            raise AssertionError(
                "No errors should have been logged. Instead got: {}".format(
                    mock_logging.getLogger.return_value.error.call_args_list
                )
            )

        assert self.sock is not None
        received = self.sock.recv(2048)

        assert received is not None
        assert len(received) > 0

        self.all_received = True
