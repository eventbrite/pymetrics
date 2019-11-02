"""isort:skip_file"""
from __future__ import absolute_import  # DO NOT import UNICODE LITERALS in this file!

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
@mock.patch('pymetrics.publishers.statsd.logging')
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
        self.sock.bind(('localhost', 0))
        self.sock.settimeout(1.0)
        return self.sock.getsockname()[1]

    def test_maximum_packet_size_constructor(self, _mock_logging):
        publisher = StatsdPublisher('127.0.0.1', 8125)
        assert publisher.maximum_packet_size == 65000

        publisher = StatsdPublisher('127.0.0.1', 8125, maximum_packet_size=1400)
        assert publisher.maximum_packet_size == 1400

        publisher = StatsdPublisher('127.0.0.1', 8125, maximum_packet_size=175000)
        assert publisher.maximum_packet_size == 65000

    def test_no_metrics_does_nothing(self, _mock_logging):
        port = self._start_udp_socket()

        publisher = StatsdPublisher('127.0.0.1', port)
        publisher.publish([])

        self.all_received = True

        assert self.sock is not None
        # noinspection PyBroadException
        try:
            bad = self.sock.recv(4096)
            raise AssertionError('Did not expect to receive any data, but received: {}'.format(bad))
        except AssertionError:
            raise
        except Exception:
            pass  # this is a good thing

    def test_no_metric_values_does_nothing(self, _mock_logging):
        port = self._start_udp_socket()

        publisher = StatsdPublisher('127.0.0.1', port)
        publisher.publish([Timer(u'hello')])

        self.all_received = True

        assert self.sock is not None
        # noinspection PyBroadException
        try:
            bad = self.sock.recv(4096)
            raise AssertionError('Did not expect to receive any data, but received: {}'.format(bad))
        except AssertionError:
            raise
        except Exception:
            pass  # this is a good thing

    def test_bytes(self, mock_logging):
        """
        Test that byte-string metric names work properly

        This function intentionally uses byte-strings for every metric it records, to ensure they get recorded properly.
        On Python 2, this test is actually different from `test_unicode`. On Python 3, they are identical (except
        the port number and gauge value).
        """

        port = self._start_udp_socket()

        metrics = [
            Counter('test_bytes.counter', initial_value=1),
            Gauge('test_bytes.gauge', initial_value=17),
            Histogram('test_bytes.histogram', initial_value=3),
            Timer('test_bytes.timer', initial_value=1),
        ]  # type: List[Metric]

        self.all_received = False

        publisher = StatsdPublisher('localhost', port)
        publisher.publish(metrics)

        # We want to make sure that no logging was called at all
        # We test it this way so that any unexpected calls are printed to the output
        if mock_logging.getLogger.return_value.error.called:
            raise AssertionError('No errors should have been logged. Instead got: {}'.format(
                mock_logging.getLogger.return_value.error.call_args_list
            ))

        self.all_received = True

        assert self.sock is not None
        received = self.sock.recv(2048)

        assert received is not None
        assert received == (
            b'test_bytes.counter:1|c\ntest_bytes.gauge:17|g\n'
            b'test_bytes.histogram:3|ms\ntest_bytes.timer:1|ms'
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
            Counter(u'test_unicode.counter', initial_value=1),
            Gauge(u'test_unicode.gauge', initial_value=42),
            Histogram(u'test_unicode.histogram', initial_value=6),
            Timer(u'test_unicode.timer', initial_value=1),
        ]  # type: List[Metric]

        self.all_received = False

        publisher = StatsdPublisher('localhost', port)
        publisher.publish(metrics)

        # We want to make sure that no logging was called at all
        # We test it this way so that any unexpected calls are printed to the output
        if mock_logging.getLogger.return_value.error.called:
            raise AssertionError('No errors should have been logged. Instead got: {}'.format(
                mock_logging.getLogger.return_value.error.call_args_list
            ))

        self.all_received = True

        assert self.sock is not None
        received = self.sock.recv(2048)

        assert received is not None
        assert received == (
            b'test_unicode.counter:1|c\ntest_unicode.gauge:42|g\ntest_unicode.histogram:6|ms\ntest_unicode.timer:1|ms'
        )

    def test_meta_metrics(self, mock_logging):
        """
        Test that meta metrics work properly

        This test confirms that, when enabled, meta-metrics are sent, informing about the performance of PyMetrics
        itself.
        """
        port = self._start_udp_socket()

        metrics = [
            Counter(u'test_meta_metrics.counter', initial_value=1),
            Gauge(u'test_meta_metrics.gauge', initial_value=9),
            Histogram(u'test_meta_metrics.histogram', initial_value=27),
            Timer(u'test_meta_metrics.timer', initial_value=1),
        ]  # type: List[Metric]

        self.all_received = False

        publisher = StatsdPublisher('localhost', port)
        publisher.publish(metrics, enable_meta_metrics=True)

        # We want to make sure that no logging was called at all
        # We test it this way so that any unexpected calls are printed to the output
        if mock_logging.getLogger.return_value.error.called:
            raise AssertionError('No errors should have been logged. Instead got: {}'.format(
                mock_logging.getLogger.return_value.error.call_args_list
            ))

        assert self.sock is not None
        received = self.sock.recv(2048)

        assert received is not None

        msg = received.decode('utf-8')

        received_regex = re.compile(
            br'^pymetrics\.meta\.publish\.statsd\.format_metrics:[0-9]+\|ms\n'
            br'test_meta_metrics\.counter:1\|c\n'
            br'test_meta_metrics\.gauge:9\|g\n'
            br'test_meta_metrics\.histogram:27|ms\n'
            br'test_meta_metrics\.timer:0\|ms$'
        )
        assert received_regex.match(received), msg

        self.all_received = True

        received = self.sock.recv(2048)
        assert received is not None

        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send:1\|c$', re.MULTILINE).search(received), msg
        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.num_metrics:5\|ms$', re.MULTILINE)\
            .search(received), msg
        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.timer:[0-9]+\|ms$', re.MULTILINE)\
            .search(received), msg
        assert not re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.error\.max_packet:1\|c$', re.MULTILINE)\
            .search(received), msg
        assert not re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.error\.unknown:1\|c$', re.MULTILINE)\
            .search(received), msg
        assert not re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.exceeds_max_packet:1\|c$', re.MULTILINE)\
            .search(received), msg
        assert not re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.exceeds_max_gig_e:1\|c$', re.MULTILINE)\
            .search(received), msg
        assert not re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.exceeds_max_fast_e:1\|c$', re.MULTILINE)\
            .search(received), msg

    @mock.patch('pymetrics.publishers.statsd.socket')
    def test_broken_up_packet_and_include_meta_metrics(self, mock_socket, _):
        """
        Test that packets get broken up properly when over the limit.

        This function tests that our metrics payload gets broken up in an orderly way to ensure that we send packets
        to Statsd that remain under the packet limit of 65,535 bytes.
        """

        mock_socket.AF_INET = socket.AF_INET
        mock_socket.SOCK_DGRAM = socket.SOCK_DGRAM
        mock_socket.error = socket.error

        socket1 = mock.MagicMock()
        socket2 = mock.MagicMock()
        socket3 = mock.MagicMock()
        socket4 = mock.MagicMock()

        mock_socket.socket.side_effect = [socket1, socket2, socket3, socket4]

        metrics = []  # type: List[Metric]
        for i in range(0, 1678):
            # 39 bytes per metric including ":1|c\n"; last metric is 38 bytes
            # 51 bytes and 47 bytes for the prepended meta-metrics
            # This is 65,543 bytes of metrics
            metrics.append(Counter(u'pysoa.test.test_bytes.counter_{:04d}'.format(i), initial_value=1))

        publisher = StatsdPublisher('localhost', 7654)
        publisher.publish(metrics, enable_meta_metrics=True)

        mock_socket.socket.assert_has_calls([
            mock.call(socket.AF_INET, socket.SOCK_DGRAM),
            mock.call(socket.AF_INET, socket.SOCK_DGRAM),
            mock.call(socket.AF_INET, socket.SOCK_DGRAM),
            mock.call(socket.AF_INET, socket.SOCK_DGRAM),
        ])

        socket1.settimeout.assert_called_once_with(0.5)
        socket1.connect.assert_called_once_with(('localhost', 7654))
        socket1.sendall.assert_called_once()
        socket1.close.assert_called_once()

        payload = socket1.sendall.call_args[0][0]
        assert len(
            re.compile(br'^pymetrics\.meta\.publish\.statsd\.format_metrics:[0-9]+\|ms$', re.MULTILINE).findall(
                payload,
            )
        ) == 1
        assert len(
            re.compile(br'^pysoa\.test\.test_bytes\.counter_\d\d\d\d:1\|c$', re.MULTILINE).findall(payload)
        ) == 1665
        assert len(payload) < 65000

        socket2.settimeout.assert_called_once_with(0.5)
        socket2.connect.assert_called_once_with(('localhost', 7654))
        socket2.sendall.assert_called_once()
        socket2.close.assert_called_once()

        payload = socket2.sendall.call_args[0][0]
        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send:1\|c$', re.MULTILINE).search(payload)
        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.num_metrics:1666\|ms$', re.MULTILINE)\
            .search(payload)
        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.timer:[0-9]+\|ms$', re.MULTILINE)\
            .search(payload)
        assert not re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.error\.max_packet:1\|c$', re.MULTILINE)\
            .search(payload)
        assert not re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.error\.unknown:1\|c$', re.MULTILINE)\
            .search(payload)
        assert not re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.exceeds_max_packet:1\|c$', re.MULTILINE)\
            .search(payload)
        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.exceeds_max_gig_e:1\|c$', re.MULTILINE)\
            .search(payload)
        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.exceeds_max_fast_e:1\|c$', re.MULTILINE)\
            .search(payload)
        assert len(payload) < 65000

        socket3.settimeout.assert_called_once_with(0.5)
        socket3.connect.assert_called_once_with(('localhost', 7654))
        socket3.sendall.assert_called_once()
        socket3.close.assert_called_once()

        payload = socket3.sendall.call_args[0][0]
        assert len(
            re.compile(br'^pymetrics\.meta\.publish\.statsd\.format_metrics:[0-9]+\|ms$', re.MULTILINE).findall(
                payload,
            )
        ) == 0
        assert len(
            re.compile(br'^pysoa\.test\.test_bytes\.counter_\d\d\d\d:1\|c$', re.MULTILINE).findall(payload)
        ) == 13
        assert len(payload) < 65000

        socket4.settimeout.assert_called_once_with(0.5)
        socket4.connect.assert_called_once_with(('localhost', 7654))
        socket4.sendall.assert_called_once()
        socket4.close.assert_called_once()

        payload = socket4.sendall.call_args[0][0]
        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send:1\|c$', re.MULTILINE)\
            .search(payload)
        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.num_metrics:13\|ms$', re.MULTILINE)\
            .search(payload)
        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.timer:[0-9]+\|ms$', re.MULTILINE)\
            .search(payload)
        assert not re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.error\.max_packet:1\|c$', re.MULTILINE)\
            .search(payload)
        assert not re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.error\.unknown:1\|c$', re.MULTILINE)\
            .search(payload)
        assert not re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.exceeds_max_packet:1\|c$', re.MULTILINE)\
            .search(payload)
        assert not re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.exceeds_max_gig_e:1\|c$', re.MULTILINE)\
            .search(payload)
        assert not re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.exceeds_max_fast_e:1\|c$', re.MULTILINE)\
            .search(payload)
        assert len(payload) < 65000

    @mock.patch('pymetrics.publishers.statsd.socket')
    def test_meta_metrics_max_packet(self, mock_socket, mock_logging):
        """
        Test that meta metrics flag packets exceeding maximum allowed packet size

        This tests that packets that don't send successfully due to exceeding the maximum packet size for a connection
        get flagged in meta metrics. We have to mock this, because the actual maximum packet size varies from one
        platform to another. We know it's 65535 on our QA/Stage/Prod servers, but it may be lower where these tests
        are running (it's 9215 on Mac OS X for some strange reason).
        """

        mock_socket.AF_INET = socket.AF_INET
        mock_socket.SOCK_DGRAM = socket.SOCK_DGRAM
        mock_socket.error = socket.error

        socket1 = mock.MagicMock()
        socket1.sendall.side_effect = socket.error(errno.EMSGSIZE, '')
        socket2 = mock.MagicMock()

        mock_socket.socket.side_effect = [socket1, socket2]

        metrics = []  # type: List[Metric]
        for i in range(0, 400):
            # 39 bytes per metric including ":1|c\n"; last metric is 38 bytes
            # 51 bytes and 47 bytes for the prepended meta-metrics
            # This is 15697 bytes of metrics
            metrics.append(Counter(u'pysoa.test.test_bytes.counter_{:04d}'.format(i), initial_value=1))

        publisher = StatsdPublisher('localhost', 1234)
        publisher.publish(metrics, error_logger='test_service', enable_meta_metrics=True)

        mock_logging.getLogger.assert_called_once_with('test_service')
        mock_logging.getLogger.return_value.error.assert_called()

        mock_socket.socket.assert_has_calls([
            mock.call(socket.AF_INET, socket.SOCK_DGRAM),
            mock.call(socket.AF_INET, socket.SOCK_DGRAM),
        ])

        socket1.settimeout.assert_called_once_with(0.5)
        socket1.connect.assert_called_once_with(('localhost', 1234))
        socket1.sendall.assert_called_once()
        assert socket1.close.called is True

        payload = socket1.sendall.call_args[0][0]
        assert len(
            re.compile(br'^pymetrics\.meta\.publish\.statsd\.format_metrics:[0-9]+\|ms$', re.MULTILINE).findall(
                payload,
            )
        ) == 1
        assert len(
            re.compile(br'^pysoa\.test\.test_bytes\.counter_\d\d\d\d:1\|c$', re.MULTILINE).findall(payload)
        ) == 400

        socket2.settimeout.assert_called_once_with(0.5)
        socket2.connect.assert_called_once_with(('localhost', 1234))
        socket2.sendall.assert_called_once()
        socket2.close.assert_called_once()

        payload = socket2.sendall.call_args[0][0]
        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send:1\|c$', re.MULTILINE).search(payload)
        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.num_metrics:401\|ms$', re.MULTILINE)\
            .search(payload)
        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.timer:[0-9]+\|ms$', re.MULTILINE)\
            .search(payload)
        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.error\.max_packet:1\|c$', re.MULTILINE)\
            .search(payload)
        assert not re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.error\.unknown:1\|c$', re.MULTILINE)\
            .search(payload)
        assert not re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.exceeds_max_packet:1\|c$', re.MULTILINE)\
            .search(payload)
        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.exceeds_max_gig_e:1\|c$', re.MULTILINE)\
            .search(payload)
        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.exceeds_max_fast_e:1\|c$', re.MULTILINE)\
            .search(payload)

    def test_meta_metrics_max_gig_e(self, mock_logging):
        """
        Test that meta metrics flag packets exceeding maximum GigE MTU

        This tests that large packets send successfully, but that meta metrics flag packets that would exceed the
        maximum MTU of gigabit Ethernet (1000).
        """

        port = self._start_udp_socket()

        metrics = []  # type: List[Metric]
        for i in range(0, 229):
            # 39 bytes per metric including ":1|c\n"; last metric is 38 bytes
            # 51 bytes and 47 bytes for the prepended meta-metrics
            # This is 8,991 bytes of metrics
            metrics.append(Counter(u'pysoa.test.test_bytes.counter_{:04d}'.format(i), initial_value=1))

        self.all_received = False

        publisher = StatsdPublisher('localhost', port)
        publisher.publish(metrics, enable_meta_metrics=True)

        # We want to make sure that no logging was called at all
        # We test it this way so that any unexpected calls are printed to the output
        if mock_logging.getLogger.return_value.error.called:
            raise AssertionError('No errors should have been logged. Instead got: {}'.format(
                mock_logging.getLogger.return_value.error.call_args_list
            ))

        assert self.sock is not None
        received = self.sock.recv(10000)
        assert received is not None

        assert len(
            re.compile(br'^pymetrics\.meta\.publish\.statsd\.format_metrics:[0-9]+\|ms$', re.MULTILINE).findall(
                received,
            )
        ) == 1
        assert len(
            re.compile(br'^pysoa\.test\.test_bytes\.counter_\d\d\d\d:1\|c$', re.MULTILINE).findall(received)
        ) == 229

        self.all_received = True

        received = self.sock.recv(2048)
        assert received is not None

        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send:1\|c$', re.MULTILINE).search(received)
        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.num_metrics:230\|ms$', re.MULTILINE)\
            .search(received)
        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.timer:[0-9]+\|ms$', re.MULTILINE)\
            .search(received)
        assert not re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.error\.max_packet:1\|c$', re.MULTILINE)\
            .search(received)
        assert not re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.error\.unknown:1\|c$', re.MULTILINE)\
            .search(received)
        assert not re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.exceeds_max_packet:1\|c$', re.MULTILINE)\
            .search(received)
        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.exceeds_max_gig_e:1\|c$', re.MULTILINE)\
            .search(received)
        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.exceeds_max_fast_e:1\|c$', re.MULTILINE)\
            .search(received)

    def test_meta_metrics_max_fast_e(self, mock_logging):
        """
        Test that meta metrics flag packets exceeding maximum Fast Ethernet MTU

        This tests that large packets send successfully, but that meta metrics flag packets that would exceed the
        maximum MTU of Fast Ethernet (10/100).
        """

        port = self._start_udp_socket()

        metrics = []  # type: List[Metric]
        for i in range(0, 37):
            # 39 bytes per metric including ":1|c\n"; last metric is 38 bytes
            # 51 bytes and 47 bytes for the prepended meta-metrics
            # This is 1,504 bytes of metrics
            metrics.append(Counter(u'pysoa.test.test_bytes.counter_{:04d}'.format(i), initial_value=1))

        self.all_received = False

        publisher = StatsdPublisher('localhost', port)
        publisher.publish(metrics, enable_meta_metrics=True)

        # We want to make sure that no logging was called at all
        # We test it this way so that any unexpected calls are printed to the output
        if mock_logging.getLogger.return_value.error.called:
            raise AssertionError('No errors should have been logged. Instead got: {}'.format(
                mock_logging.getLogger.return_value.error.call_args_list
            ))

        assert self.sock is not None
        received = self.sock.recv(2048)
        assert received is not None

        assert len(
            re.compile(br'^pymetrics\.meta\.publish\.statsd\.format_metrics:[0-9]+\|ms$', re.MULTILINE).findall(
                received,
            )
        ) == 1
        assert len(
            re.compile(br'^pysoa\.test\.test_bytes\.counter_\d\d\d\d:1\|c$', re.MULTILINE).findall(received)
        ) == 37

        self.all_received = True

        received = self.sock.recv(2048)
        assert received is not None

        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send:1\|c$', re.MULTILINE).search(received)
        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.num_metrics:38\|ms$', re.MULTILINE)\
            .search(received)
        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.timer:[0-9]+\|ms$', re.MULTILINE)\
            .search(received)
        assert not re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.error\.max_packet:1\|c$', re.MULTILINE)\
            .search(received)
        assert not re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.error\.unknown:1\|c$', re.MULTILINE)\
            .search(received)
        assert not re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.exceeds_max_packet:1\|c$', re.MULTILINE)\
            .search(received)
        assert not re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.exceeds_max_gig_e:1\|c$', re.MULTILINE)\
            .search(received)
        assert re.compile(br'^pymetrics\.meta\.publish\.statsd\.send\.exceeds_max_fast_e:1\|c$', re.MULTILINE)\
            .search(received)
