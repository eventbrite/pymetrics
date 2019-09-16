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
        with pytest.raises(ValueError):
            # noinspection PyTypeChecker
            DogStatsdPublisher('localhost', '1234', global_tags=['this', 'is', 'invalid'])  # type: ignore

    def test_extra_gauge_tags_invalid(self):
        with pytest.raises(ValueError):
            # noinspection PyTypeChecker
            DogStatsdPublisher('localhost', '1234', extra_gauge_tags=['this', 'is', 'invalid'])  # type: ignore

    def test_no_metrics_does_nothing(self):
        publisher = DogStatsdPublisher('127.0.0.1', 8125)
        assert publisher.get_formatted_metrics([]) == []

    def test_no_metric_values_does_nothing(self):
        publisher = DogStatsdPublisher('127.0.0.1', 8125)
        assert publisher.get_formatted_metrics([Timer(u'hello')]) == []

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
            [b'test.foo.timer.1:1|c', b'test.bar.gauge.1:5|g', b'test.baz.timer.1:2|ms', b'test.qux.histogram.1:13|h']
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
                b'test.foo.timer.1:1|c|#blank_tag',
                b'test.bar.gauge.1:5|g|#blank_tag',
                b'test.baz.timer.1:2|ms|#blank_tag',
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
                b'test.baz.timer.1:2|ms|#integration:abc123',
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
                b'test.foo.timer.1:1|c|#environment:qa,acceptance,jenkins-build:8293847',
                b'test.bar.gauge.1:5|g|#environment:qa,acceptance,jenkins-build:8293847',
                b'test.baz.timer.1:2|ms|#environment:qa,acceptance,jenkins-build:8293847',
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
                b'test.baz.timer.1:2|ms|#integration:abc123',
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
                b'test.baz.timer.1:2|ms',
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
        assert metrics[2] == b'test.baz.timer.1:2|ms|#number:5791'

        assert metrics[1].startswith(b'test.bar.gauge.1:5|g|#')
        assert b'extra:data' in metrics[1]
        assert b'nothing' in metrics[1]
        assert b'nothing:' not in metrics[1]
        assert b'mail:snail' in metrics[1]
        assert b'guitar:electric' in metrics[1]

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

        metrics = publisher.get_formatted_metrics([counter, gauge, timer], enable_meta_metrics=True)

        assert metrics[0].startswith(b'pymetrics.meta.publish.statsd.format_metrics:')
        assert metrics[0].endswith(b'|ms|#environment:qa,acceptance,jenkins-build:8293847')

        assert metrics[1] == b'test.foo.timer.1:1|c|#environment:qa,acceptance,jenkins-build:8293847,hello:world'

        assert metrics[2].startswith(
            b'test.bar.gauge.1:5|g|#environment:qa,acceptance,jenkins-build:8293847,worker:52,'
        )
        assert b',extra:data' in metrics[2]
        assert b',nothing' in metrics[2]
        assert b',nothing:' not in metrics[2]
        assert b',mail:snail' in metrics[2]
        assert b',guitar:electric' in metrics[2]

        assert metrics[3].startswith(b'test.baz.timer.1:2|ms|#environment:qa,acceptance,jenkins-build:8293847')
        assert b',number:5791.15' in metrics[3]
        assert b',other_number:0' in metrics[3]

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

        metrics = publisher.get_formatted_metrics([counter, gauge, timer, histogram], enable_meta_metrics=True)

        assert metrics[0].startswith(b'pymetrics.meta.publish.statsd.format_metrics:')
        assert metrics[0].endswith(b'|d|#environment:qa,acceptance,jenkins-build:8293847')

        assert metrics[1] == b'test.foo.timer.1:1|c|#environment:qa,acceptance,jenkins-build:8293847,hello:world'

        assert metrics[2].startswith(
            b'test.bar.gauge.1:5|g|#environment:qa,acceptance,jenkins-build:8293847,worker:52,'
        )
        assert b',extra:data' in metrics[2]
        assert b',nothing' in metrics[2]
        assert b',nothing:' not in metrics[2]
        assert b',mail:snail' in metrics[2]
        assert b',guitar:electric' in metrics[2]

        assert metrics[3].startswith(b'test.baz.timer.1:2|d|#environment:qa,acceptance,jenkins-build:8293847')
        assert b',number:5791.15' in metrics[3]
        assert b',other_number:0' in metrics[3]

        assert metrics[4].startswith(
            b'test.qux.histogram.1:91|d|#environment:qa,acceptance,jenkins-build:8293847,'
        )
        assert b',extra:data' in metrics[4]
        assert b',nothing' in metrics[4]
        assert b',nothing:' not in metrics[4]
        assert b',mail:snail' in metrics[4]
        assert b',guitar:electric' in metrics[4]
