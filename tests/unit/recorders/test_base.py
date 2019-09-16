from __future__ import (
    absolute_import,
    unicode_literals,
)

from typing import cast

import mock

from pymetrics.instruments import (
    Counter,
    Timer,
    TimerResolution,
)
from pymetrics.recorders.base import (
    MetricsRecorder,
    metric_decorator,
)


class TestMetricDecorator(object):
    def setup_method(self, _method):
        # noinspection PyAttributeOutsideInit
        self.recorder = mock.MagicMock()

    def reset(self):
        self.recorder.reset_mock()
        self.recorder.counter.return_value = Counter('')
        self.recorder.timer.return_value = Timer('')

    def counter(self, name, *args, **kwargs):
        return metric_decorator(
            lambda: cast(MetricsRecorder, self.recorder),
            'counter',
            name,
            *args,
            **kwargs
        )

    def timer(self, name, *args, **kwargs):
        return metric_decorator(
            lambda: cast(MetricsRecorder, self.recorder),
            'timer',
            name,
            *args,
            **kwargs
        )

    def test_counter_decorator(self):
        @self.counter('a.neat.counter', tag_1='value_1')
        def counted(foo):
            assert foo == 'bar'
            return 'counted_return'

        self.reset()
        assert counted('bar') == 'counted_return'
        self.recorder.counter.assert_called_once_with('a.neat.counter', tag_1='value_1')
        assert self.recorder.timer.call_count == 0

        self.reset()
        assert counted(foo='bar') == 'counted_return'
        self.recorder.counter.assert_called_once_with('a.neat.counter', tag_1='value_1')
        assert self.recorder.timer.call_count == 0

    def test_timer_decorator(self):
        @self.timer('a.cool.timer', resolution=TimerResolution.MICROSECONDS, include_metric=True, tag_2='value_2')
        def timed(bar, metric):
            assert bar == 'baz'
            assert metric is self.recorder.timer.return_value
            return 'timed_return'

        self.reset()
        assert timed('baz') == 'timed_return'
        self.recorder.timer.assert_called_once_with(
            'a.cool.timer',
            resolution=TimerResolution.MICROSECONDS,
            tag_2='value_2',
        )
        assert self.recorder.counter.call_count == 0

        self.reset()
        assert timed(bar='baz') == 'timed_return'
        self.recorder.timer.assert_called_once_with(
            'a.cool.timer',
            resolution=TimerResolution.MICROSECONDS,
            tag_2='value_2',
        )
        assert self.recorder.counter.call_count == 0

    def test_combined_decorators(self):
        @self.counter('one.more.counter', 3, include_metric=True)
        @self.timer('one.more.timer')
        def counted_and_timed(baz, metric):
            assert baz == 'qux'
            assert metric is self.recorder.counter.return_value
            return 'counted_and_timed_return'

        self.reset()
        assert counted_and_timed('qux') == 'counted_and_timed_return'
        self.recorder.counter.assert_called_once_with('one.more.counter', 3)
        self.recorder.timer.assert_called_once_with('one.more.timer')

        self.reset()
        assert counted_and_timed(baz='qux') == 'counted_and_timed_return'
        self.recorder.counter.assert_called_once_with('one.more.counter', 3)
        self.recorder.timer.assert_called_once_with('one.more.timer')
