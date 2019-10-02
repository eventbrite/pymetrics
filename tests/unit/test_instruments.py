from __future__ import (
    absolute_import,
    unicode_literals,
)

import datetime

import freezegun
import pytest

from pymetrics.instruments import (
    Counter,
    Gauge,
    Histogram,
    Metric,
    Timer,
    TimerResolution,
)


def test_cannot_instantiate_metric():
    with pytest.raises(TypeError) as error_context:
        Metric('does not matter')

    assert error_context.value.args[0] == 'Cannot instantiate abstract class "Metric"'


# noinspection PyTypeChecker
def test_invalid_name():
    with pytest.raises(TypeError) as error_context:
        Timer(None)  # type: ignore

    assert error_context.value.args[0] == 'Metric names must be non-null strings'

    with pytest.raises(TypeError) as error_context:
        Timer(1)  # type: ignore

    assert error_context.value.args[0] == 'Metric names must be non-null strings'


# noinspection PyTypeChecker
def test_invalid_initial_value():
    with pytest.raises(TypeError) as error_context:
        Timer('Hello', None)  # type: ignore

    assert error_context.value.args[0] == 'Metric values must be integers or floats'

    with pytest.raises(TypeError) as error_context:
        Timer('Hello', 'Not an int')  # type: ignore

    assert error_context.value.args[0] == 'Metric values must be integers or floats'


# noinspection PyTypeChecker
def test_counter_invalid_initial_value():
    with pytest.raises(TypeError) as error_context:
        Counter('Hello', None)  # type: ignore

    assert error_context.value.args[0] == 'Counter values must be non-null, non-negative integers'

    with pytest.raises(TypeError) as error_context:
        Counter('Hello', 1.1)  # type: ignore

    assert error_context.value.args[0] == 'Counter values must be non-null, non-negative integers'

    with pytest.raises(TypeError) as error_context:
        Counter('Hello', -1)  # type: ignore

    assert error_context.value.args[0] == 'Counter values must be non-null, non-negative integers'


# noinspection PyTypeChecker
def test_gauge_invalid_initial_value():
    with pytest.raises(TypeError) as error_context:
        Gauge('Hello', None)  # type: ignore

    assert error_context.value.args[0] == 'Gauge values must be non-null, non-negative integers'

    with pytest.raises(TypeError) as error_context:
        Gauge('Hello', 1.1)  # type: ignore

    assert error_context.value.args[0] == 'Gauge values must be non-null, non-negative integers'

    with pytest.raises(TypeError) as error_context:
        Gauge('Hello', -1)  # type: ignore

    assert error_context.value.args[0] == 'Gauge values must be non-null, non-negative integers'


def test_counter():
    counter = Counter('test.counter.1', tag_1='value_1')

    assert counter.name == 'test.counter.1'
    assert counter.tags['tag_1'] == 'value_1'
    assert counter.value == 0

    assert counter.increment() == 1
    assert counter.value == 1

    assert counter.increment(2) == 3
    assert counter.value == 3

    assert counter.reset() == 0
    assert counter.value == 0

    assert counter.reset(5) == 5
    assert counter.value == 5

    with pytest.raises(ValueError):
        counter.reset(-1)

    counter = Counter('test.counter.2', initial_value=3)

    assert counter.name == 'test.counter.2'
    assert not counter.tags
    assert counter.value == 3

    assert counter.increment(5) == 8
    assert counter.value == 8

    assert counter.reset() == 3
    assert counter.value == 3

    def around(foo, bar):
        assert foo == 'baz'
        assert bar == 'qux'
        return 'Lorem'

    assert counter.record_over_function(around, 'baz', bar='qux') == 'Lorem'
    assert counter.value == 4

    assert repr(counter) == 'Counter(name="test.counter.2", value=4)'


def test_gauge():
    gauge = Gauge('test.gauge.1', tag_2='value_2')

    assert gauge.name == 'test.gauge.1'
    assert gauge.tags['tag_2'] == 'value_2'
    assert gauge.value == 0

    assert gauge.set(3) == 3
    assert gauge.value == 3

    assert gauge.set() == 0
    assert gauge.value == 0

    with pytest.raises(ValueError):
        gauge.set(-1)

    gauge = Gauge('test.gauge.2', initial_value=7)

    assert gauge.name == 'test.gauge.2'
    assert not gauge.tags
    assert gauge.value == 7

    assert gauge.set(3) == 3
    assert gauge.value == 3

    assert gauge.set() == 7
    assert gauge.value == 7

    assert repr(gauge) == 'Gauge(name="test.gauge.2", value=7)'

    def around():
        pass

    with pytest.raises(TypeError):
        gauge.record_over_function(around)


def test_histogram():
    histogram = Histogram('test.histogram.1', tag_3='value_3')

    assert histogram.name == 'test.histogram.1'
    assert histogram.tags['tag_3'] == 'value_3'
    assert histogram.value == 0

    assert histogram.set(3) == 3
    assert histogram.value == 3

    assert histogram.set(1.7) == 2
    assert histogram.value == 2

    assert histogram.set() == 0
    assert histogram.value == 0

    with pytest.raises(ValueError):
        histogram.set(-1)

    histogram = Histogram('test.histogram.2', initial_value=7.5)

    assert histogram.name == 'test.histogram.2'
    assert not histogram.tags
    assert histogram.value == 8

    assert histogram.set(3.2) == 3
    assert histogram.value == 3

    assert histogram.set() == 8
    assert histogram.value == 8

    assert repr(histogram) == 'Histogram(name="test.histogram.2", value=8)'

    def around():
        pass

    with pytest.raises(TypeError):
        histogram.record_over_function(around)


def _milliseconds(m):
    return datetime.timedelta(milliseconds=m)


def _microseconds(m):
    return datetime.timedelta(microseconds=m)


def test_timer():
    timer = Timer('test.timer.1', tag_4='value_4')

    assert timer.name == 'test.timer.1'
    assert timer.tags['tag_4'] == 'value_4'
    assert timer.value is None

    timer = Timer('test.timer.2', initial_value=3.75)

    assert timer.name == 'test.timer.2'
    assert not timer.tags
    assert timer.value == 4

    with freezegun.freeze_time() as frozen_time:
        timer.start()
        frozen_time.tick(_milliseconds(15))
        timer.stop()

        assert timer.value == 15

        timer.start()
        frozen_time.tick(_milliseconds(27))
        timer.stop()

        assert timer.value == 42

        with timer:
            frozen_time.tick(_milliseconds(8))
            frozen_time.tick(_microseconds(100))

        assert timer.value == 50

        def around(foo, bar):
            assert foo == 'baz'
            assert bar == 'qux'
            frozen_time.tick(_milliseconds(11))
            frozen_time.tick(_microseconds(600))
            return 'Ipsum'

        assert timer.record_over_function(around, 'baz', bar='qux') == 'Ipsum'
        assert timer.value == 62

    timer = Timer('test.timer.3', resolution=TimerResolution.MICROSECONDS)

    with freezegun.freeze_time() as frozen_time:
        timer.start()
        frozen_time.tick(_milliseconds(1))
        frozen_time.tick(_microseconds(103))
        timer.stop()

        assert timer.value == 1103

        with timer:
            frozen_time.tick(_microseconds(209))

        assert timer.value == 1312

        timer.start()
        assert timer.value is None

        frozen_time.tick(_milliseconds(2))
        timer.stop()
        assert timer.value == 3312

    assert repr(timer) == 'Timer(name="test.timer.3", value=3312)'

    # make sure no error is raised, nothing happens
    timer.stop()
    timer.stop()
    timer.stop()

    assert repr(timer) == 'Timer(name="test.timer.3", value=3312)'
