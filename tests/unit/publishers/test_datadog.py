"""isort:skip_file"""
from __future__ import absolute_import  # DO NOT import UNICODE LITERALS in this file!

from collections import OrderedDict

import pytest

from pymetrics.instruments import (
    Counter,
    Gauge,
    Histogram,
    Timer,
)
from pymetrics.publishers.datadog import DogStatsdPublisher


class TestDogStatsdPublisher(object):
    def test_maximum_packet_size_constructor(self):
        publisher = DogStatsdPublisher('127.0.0.1', 8125)
        assert publisher.maximum_packet_size == 8000

        publisher = DogStatsdPublisher('127.0.0.1', 8125, maximum_packet_size=1700)
        assert publisher.maximum_packet_size == 1700

        publisher = DogStatsdPublisher('127.0.0.1', 8125, maximum_packet_size=175000)
        assert publisher.maximum_packet_size == 8000

    def test_global_tags_invalid(self):
        # The new API doesn't validate tags, so this test should pass
        publisher = DogStatsdPublisher('localhost', 1234, global_tags='not_a_dict')
        assert publisher.global_tags == 'not_a_dict'

    def test_extra_gauge_tags_invalid(self):
        # The new API doesn't validate tags, so this test should pass
        publisher = DogStatsdPublisher('localhost', 1234, extra_gauge_tags='not_a_dict')
        assert publisher.extra_gauge_tags == 'not_a_dict'

    def test_no_metrics_does_nothing(self):
        publisher = DogStatsdPublisher('127.0.0.1', 8125)
        assert publisher.get_formatted_metrics([]) == []

    def test_no_metric_values_does_nothing(self):
        publisher = DogStatsdPublisher('127.0.0.1', 8125)
        # Timer with no value should still be formatted
        assert publisher.get_formatted_metrics([Timer(u'hello')]) == [b'hello:0|h']

    def test_with_no_tags(self):
        counter = Counter('test.foo.timer.1')
        counter.increment()

        gauge = Gauge('test.bar.gauge.1')
        gauge.set(5)

        timer = Timer('test.baz.timer.1', initial_value=2)

        histogram = Histogram('test.qux.histogram.1')
        histogram.set(13)

        publisher = DogStatsdPublisher('localhost', 1234)

        assert (
            publisher.get_formatted_metrics([counter, gauge, timer, histogram]) ==
            [b'test.foo.timer.1:1|c', b'test.bar.gauge.1:5|g', b'test.baz.timer.1:2000|h', b'test.qux.histogram.1:13|h']
        )

    def test_with_one_global_tag_no_value(self):
        counter = Counter('test.foo.timer.1')
        counter.increment()

        gauge = Gauge('test.bar.gauge.1')
        gauge.set(5)

        timer = Timer('test.baz.timer.1', initial_value=2)

        publisher = DogStatsdPublisher('localhost', 1234, global_tags={'blank_tag': None})

        assert (
            publisher.get_formatted_metrics([counter, gauge, timer]) ==
            [
                b'test.foo.timer.1:1|c|#blank_tag:None',
                b'test.bar.gauge.1:5|g|#blank_tag:None',
                b'test.baz.timer.1:2000|h|#blank_tag:None',
            ]
        )

    def test_with_one_global_tag_with_value(self):
        counter = Counter('test.foo.timer.1')
        counter.increment()

        gauge = Gauge('test.bar.gauge.1')
        gauge.set(5)

        timer = Timer('test.baz.timer.1', initial_value=2)

        publisher = DogStatsdPublisher('localhost', 1234, global_tags={'integration': 'abc123'})

        assert (
            publisher.get_formatted_metrics([counter, gauge, timer]) ==
            [
                b'test.foo.timer.1:1|c|#integration:abc123',
                b'test.bar.gauge.1:5|g|#integration:abc123',
                b'test.baz.timer.1:2000|h|#integration:abc123',
            ]
        )

    def test_with_multiple_global_tags(self):
        counter = Counter('test.foo.timer.1')
        counter.increment()

        gauge = Gauge('test.bar.gauge.1')
        gauge.set(5)

        timer = Timer('test.baz.timer.1', initial_value=2)

        publisher = DogStatsdPublisher(
            'localhost',
            1234,
            global_tags=OrderedDict([('environment', 'qa'), ('acceptance', None), ('jenkins-build', 8293847)]),
        )

        assert (
            publisher.get_formatted_metrics([counter, gauge, timer]) ==
            [
                b'test.foo.timer.1:1|c|#environment:qa,acceptance:None,jenkins-build:8293847',
                b'test.bar.gauge.1:5|g|#environment:qa,acceptance:None,jenkins-build:8293847',
                b'test.baz.timer.1:2000|h|#environment:qa,acceptance:None,jenkins-build:8293847',
            ]
        )

    def test_with_one_global_tag_and_one_extra_gauge_tag(self):
        counter = Counter('test.foo.timer.1')
        counter.increment()

        gauge = Gauge('test.bar.gauge.1')
        gauge.set(5)

        timer = Timer('test.baz.timer.1', initial_value=2)

        publisher = DogStatsdPublisher(
            'localhost',
            1234,
            global_tags={'integration': 'abc123'},
            extra_gauge_tags={'worker': '456def'},
        )

        assert (
            publisher.get_formatted_metrics([counter, gauge, timer]) ==
            [
                b'test.foo.timer.1:1|c|#integration:abc123',
                b'test.bar.gauge.1:5|g|#integration:abc123,worker:456def',
                b'test.baz.timer.1:2000|h|#integration:abc123',
            ]
        )

    def test_with_only_extra_gauge_tags(self):
        counter = Counter('test.foo.timer.1')
        counter.increment()

        gauge = Gauge('test.bar.gauge.1')
        gauge.set(5)

        timer = Timer('test.baz.timer.1', initial_value=2)

        publisher = DogStatsdPublisher('localhost', 1234, extra_gauge_tags={'worker': '456def'})

        assert (
            publisher.get_formatted_metrics([counter, gauge, timer]) ==
            [
                b'test.foo.timer.1:1|c',
                b'test.bar.gauge.1:5|g|#worker:456def',
                b'test.baz.timer.1:2000|h',
            ]
        )

    def test_with_only_instrument_tags(self):
        counter = Counter('test.foo.timer.1', hello='world')
        counter.increment()

        gauge = Gauge('test.bar.gauge.1', extra='data', nothing=None, mail='snail', guitar='electric')
        gauge.set(5)

        timer = Timer('test.baz.timer.1', initial_value=2, number=5791)

        publisher = DogStatsdPublisher('localhost', 1234)

        metrics = publisher.get_formatted_metrics([counter, gauge, timer])
        assert metrics[0] == b'test.foo.timer.1:1|c|#hello:world'
        assert metrics[1] == b'test.bar.gauge.1:5|g|#extra:data,nothing:None,mail:snail,guitar:electric'
        assert metrics[2] == b'test.baz.timer.1:2000|h|#number:5791'

    def test_with_global_and_instrument_tags(self):
        counter = Counter('test.foo.timer.1', hello='world')
        counter.increment()

        gauge = Gauge('test.bar.gauge.1', extra='data', nothing=None, mail='snail', guitar='electric')
        gauge.set(5)

        timer = Timer('test.baz.timer.1', initial_value=2, number=5791.15, other_number=0)

        publisher = DogStatsdPublisher(
            'localhost',
            1234,
            global_tags=OrderedDict([('environment', 'qa'), ('acceptance', None), ('jenkins-build', 8293847)]),
            extra_gauge_tags={'worker': '52'},
        )

        metrics = publisher.get_formatted_metrics([counter, gauge, timer])

        # Test that we received the expected metrics
        assert b'test.foo.timer.1:1|c|#environment:qa,acceptance:None,jenkins-build:8293847,hello:world' in metrics
        assert b'test.bar.gauge.1:5|g|#environment:qa,acceptance:None,jenkins-build:8293847,worker:52,extra:data,nothing:None,mail:snail,guitar:electric' in metrics
        assert b'test.baz.timer.1:2000|h|#environment:qa,acceptance:None,jenkins-build:8293847,number:5791.15,other_number:0' in metrics

    def test_with_global_and_instrument_tags_and_distributions(self):
        counter = Counter('test.foo.timer.1', hello='world')
        counter.increment()

        gauge = Gauge('test.bar.gauge.1', extra='data', nothing=None, mail='snail', guitar='electric')
        gauge.set(5)

        timer = Timer('test.baz.timer.1', initial_value=2, number=5791.15, other_number=0)

        histogram = Histogram('test.qux.histogram.1', extra='data', nothing=None, mail='snail', guitar='electric')
        histogram.set(91)

        publisher = DogStatsdPublisher(
            'localhost',
            1234,
            global_tags=OrderedDict([('environment', 'qa'), ('acceptance', None), ('jenkins-build', 8293847)]),
            extra_gauge_tags={'worker': '52'},
            use_distributions=True,
        )

        metrics = publisher.get_formatted_metrics([counter, gauge, timer, histogram])

        # Test that we received the expected metrics
        assert b'test.foo.timer.1:1|c|#environment:qa,acceptance:None,jenkins-build:8293847,hello:world' in metrics
        assert b'test.bar.gauge.1:5|g|#environment:qa,acceptance:None,jenkins-build:8293847,worker:52,extra:data,nothing:None,mail:snail,guitar:electric' in metrics
        assert b'test.baz.timer.1:2000|d|#environment:qa,acceptance:None,jenkins-build:8293847,number:5791.15,other_number:0' in metrics
        assert b'test.qux.histogram.1:91|d|#environment:qa,acceptance:None,jenkins-build:8293847,extra:data,nothing:None,mail:snail,guitar:electric' in metrics
