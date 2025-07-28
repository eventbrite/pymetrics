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
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

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
    "MetricsRecorder",
    "metric_decorator",
)


M = TypeVar("M", bound=Metric)
R = TypeVar("R")


class MetricsRecorder(abc.ABC):
    """
    Abstract base class for all metrics recorders.
    """

    @abc.abstractmethod
    def record_counter(self, name, value=1, **tags):
        # type: (str, int, **Tag) -> Counter
        """
        Record a counter metric.

        :param name: The name of the counter
        :param value: The value to increment by
        :param tags: Additional tags for the counter

        :return: The counter instance
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def record_histogram(self, name, value, **tags):
        # type: (str, bool, int, **Tag) -> Histogram
        """
        Record a histogram metric.

        :param name: The name of the histogram
        :param value: The value to record
        :param tags: Additional tags for the histogram

        :return: The histogram instance
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def record_timer(self, name, value, resolution=None, **tags):
        # type: (str, bool, TimerResolution, int, **Tag) -> Timer
        """
        Record a timer metric.

        :param name: The name of the timer
        :param value: The value to record
        :param resolution: The resolution to use
        :param tags: Additional tags for the timer

        :return: The timer instance
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def record_gauge(self, name, value, **tags):
        # type: (str, bool, int, **Tag) -> Gauge
        """
        Record a gauge metric.

        :param name: The name of the gauge
        :param value: The value to set
        :param tags: Additional tags for the gauge

        :return: The gauge instance
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_metrics(self):
        # type: () -> List[Metric]
        """
        Get all recorded metrics.

        :return: A list of all metrics
        """
        raise NotImplementedError()

    def configure(self, config=None):
        # type: (Optional[Dict[str, Any]]) -> None
        """
        Configure this recorder.

        :param config: The configuration dictionary
        """
        pass


def metric_decorator(
    recorder_fetcher,  # type: Callable[[], MetricsRecorder]
    metric_type,  # type: str
    metric_name,  # type: str
    *metric_args,  # type: Any
    **metric_kwargs,  # type: Any
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
            include_metric = m_kwargs.pop(str("include_metric"), False)

            recorder = recorder_fetcher()
            method = getattr(recorder, metric_type)
            metric = method(metric_name, *copy.deepcopy(metric_args), **m_kwargs)

            if include_metric:
                kwargs[str("metric")] = metric

            return metric.record_over_function(f, *args, **kwargs)

        return wrapper

    return real_decorator
