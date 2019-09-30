from __future__ import (
    absolute_import,
    unicode_literals,
)

import abc
import copy
import functools
from typing import (
    Any,
    Callable,
    TypeVar,
)

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


__all__ = (
    'MetricsRecorder',
    'metric_decorator',
)


M = TypeVar('M', bound=Metric)
R = TypeVar('R')


@six.add_metaclass(abc.ABCMeta)
class MetricsRecorder(object):
    @abc.abstractmethod
    def counter(self, name, initial_value=0, **tags):
        # type: (six.text_type, int, **Tag) -> Counter
        """
        Creates a new counter and prepares it for publishing. The initial value is 0 if not specified. Increment the
        counter after it is returned if you do not specify an initial value.

        :param name: The name of the metric
        :param initial_value: The initial value, which defaults to 0
        :param tags: An additional tags you want associated with this metric
        :return: the created counter.
        """

    @abc.abstractmethod
    def histogram(self, name, force_new=False, initial_value=0, **tags):
        # type: (six.text_type, bool, int, **Tag) -> Histogram
        """
        Creates a new histogram for recording arbitrary numbers that can be averaged and summed. The initial value is
        0 if not specified. Set the value after it is returned if you do not specify an initial value.

        :param name: The name of the metric
        :param force_new: Whether to force the creation of a new histogram if there is already an unpublished
                          histogram with the same name and tags.
        :param initial_value: The initial value, which defaults to 0
        :param tags: An additional tags you want associated with this metric
        :return: the created histogram.
        """

    @abc.abstractmethod
    def timer(self, name, force_new=False, resolution=TimerResolution.MILLISECONDS, initial_value=0, **tags):
        # type: (six.text_type, bool, TimerResolution, int, **Tag) -> Timer
        """
        Creates and starts new timer, a special type of histogram that is recorded around the passage of time. The
        initial value is 0 if not specified, and in most cases you should not specify an initial value. The default
        resolution is milliseconds, which is suitable for most use cases. The returned timer will need to be stopped
        before it can be published (or it will be ignored on publication). However, the returned timer is also a
        context manager, so it will stop itself if you surround the code you wish to measure with `with timer(...)`.

        :param name: The name of the metric
        :param force_new: Whether to force the creation of a new timer if there is already an unpublished timer with
                          the same name and tags.
        :param resolution: The resolution at which the timer should record, which defaults to milliseconds
        :param initial_value: The initial value, which defaults to 0
        :param tags: An additional tags you want associated with this metric
        :return: the created and started timer.
        """

    @abc.abstractmethod
    def gauge(self, name, force_new=False, initial_value=0, **tags):
        # type: (six.text_type, bool, int, **Tag) -> Gauge
        """
        Creates a new gauge and prepares it for publishing. The initial value is 0 if not specified. Set the value
        after it is returned if you do not specify an initial value.

        :param name: The name of the metric
        :param force_new: Whether to force the creation of a new gauge if there is already an unpublished gauge with
                          the same name and tags.
        :param initial_value: The initial value, which defaults to 0
        :param tags: An additional tags you want associated with this metric
        :return: the created gauge.
        """

    @abc.abstractmethod
    def publish_all(self):
        # type: () -> None
        """
        Publishes all metrics that have been recorded since the last publish.
        """

    @abc.abstractmethod
    def publish_if_full_or_old(self, max_metrics=18, max_age=10):
        # type: (int, int) -> None
        """
        Publishes all metrics if at least this many metrics have been recorded *or* at least this much time has elapsed
        from the previous publish.

        :param max_metrics: If the recorder is holding at least this many metrics, publish now (defaults to 18, which
                            is a likely-safe amount assuming an MTU of 1500, which is the MTU for Docker containers)
        :param max_age: If the recorder last published at least this many seconds ago, publish now, even if the
                        recorder isn't "full" (isn't holding on to at least `max_metrics`).
        """

    @abc.abstractmethod
    def throttled_publish_all(self, delay=10):
        # type: (int) -> None
        """
        Publishes all metrics that have been recorded since the last publish unless it has been lest than `delay`
        seconds since the last publish.

        :param delay: The minimum number of seconds between publishes
        """

    @abc.abstractmethod
    def clear(self, only_published=False):
        # type: (bool) -> None
        """
        Clear all metrics that have been recorded. However, if `only_published` is `True`, histograms (and timers)
        that have not been published will not be cleared.

        :param only_published: Whether to leave unpublished histograms
        """


def metric_decorator(
    recorder_fetcher,  # type: Callable[[], MetricsRecorder]
    metric_type,  # type: six.text_type
    metric_name,  # type: six.text_type
    *metric_args,  # type: Any
    **metric_kwargs  # type: Any
):
    # type: (...) -> Callable[[Callable[..., R]], Callable[..., R]]
    """
    This decorator can be used on a function or method to provide a shorthand for obtaining the current
    :class:`MetricsRecorder` and using it to record a metric around the function invocation. This is an abstract
    decorator and should be wrapped with your own function to fetch the `MetricsRecorder` in the way you have designed
    for your application.

    Example usage:

    .. code-block:: python

        def timer(name, *args, **kwargs):
            return metrics_decorator(
                some_func_that_returns_a_metrics_recorder,
                'timer',
                name,
                *args,
                **kwargs,
            )

        ...

        @timer('timer_name')
        def some_function(...):
            do_things()

    Multiple metrics can be chained this way, too:

    .. code-block:: python

        @timer('timer_name')
        @timer('other_timer_name')
        @counter('some_counter')
        def some_function(...):
            do_things()

    If `metric_decorator` is called with the `bool` keyword-only argument `include_metric`, the created :class:`Metric`
    instrument will be passed to the wrapped function or method with an extra keyword argument named `metric`.

    :param recorder_fetcher: A callable that returns a :class:`MetricsRecorder` instance
    :param metric_type: A string with value `timer` or `counter` (other instruments currently do not support being
                        called with a decorator)
    :param metric_name: The metric name to use
    :param metric_args: The positional arguments passed to the metric
    :param metric_kwargs: The keyword arguments passed to the metric
    """
    def real_decorator(f):  # type: (Callable[..., R]) -> Callable[..., R]
        @functools.wraps(f)
        def wrapper(*args, **kwargs):  # type: (*Any, **Any) -> R
            m_kwargs = copy.deepcopy(metric_kwargs)
            include_metric = m_kwargs.pop(str('include_metric'), False)

            metric = getattr(recorder_fetcher(), metric_type)(metric_name, *copy.deepcopy(metric_args), **m_kwargs)

            if include_metric:
                kwargs[str('metric')] = metric

            return metric.record_over_function(f, *args, **kwargs)

        return wrapper

    return real_decorator
