from __future__ import (
    absolute_import,
    unicode_literals,
)

import enum
import time
from typing import (
    Any,
    Callable,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import six


try:
    from typing import Literal  # type: ignore
except ImportError:
    from typing_extensions import Literal


__all__ = (
    'Counter',
    'Gauge',
    'Histogram',
    'Metric',
    'Tag',
    'Timer',
    'TimerResolution',
)


R = TypeVar('R')

Tag = Union[six.text_type, six.binary_type, int, float, bool, None]


_valid_initial_values = (int, float)  # type: Tuple[Type, ...]
if six.PY2:
    # noinspection PyUnresolvedReferences
    _valid_initial_values += (long, )  # noqa: F821


class Metric(object):
    """
    A base metric instrument from which all metric instruments inherit. Cannot be instantiated directly.
    """

    def __init__(self, name, initial_value=0, **tags):
        # type: (six.text_type, Union[int, float], **Tag) -> None
        """
        Construct a metric.

        :param name: The metric name
        :param initial_value: The initial value of this metric, which may be an integer or a float (which will be
                              rounded)
        :param tags: The tags associated with this metric (not that not all publishers will support tags)
        """
        if self.__class__ == Metric:
            raise TypeError('Cannot instantiate abstract class "Metric"')
        if not isinstance(name, six.string_types):
            raise TypeError('Metric names must be non-null strings')
        if not isinstance(initial_value, _valid_initial_values):
            raise TypeError('Metric values must be integers or floats')

        self.name = name
        self._initial_value = initial_value
        self._value = self._initial_value
        self.tags = tags

    @property
    def value(self):  # type: () -> Optional[int]
        """
        Returns the value of this metric.

        :return: The metric value
        """
        return int(round(float(self._value)))

    def record_over_function(self, f, *args, **kwargs):  # type: (Callable[..., R], *Any, **Any) -> R
        """
        Records this metric around calling the specified callable with the specified positional and keyword arguments.
        Not all metric types support this. Raises `TypeError` when unsupported.

        :param f: The callable to invoke
        :param args: The positional arguments to pass to the callable
        :param kwargs: The keyword arguments to pass to the callable

        :return: The value the callable returns, unaltered
        """
        raise TypeError('{}s do not support use as a decorator'.format(self.__class__.__name__))

    def __repr__(self):
        return '{}(name="{}", value={})'.format(self.__class__.__name__, self.name, self.value)


class Counter(Metric):
    """
    A counter, for counting the number of times some thing has happened.
    """

    def __init__(self, name, initial_value=0, **tags):  # type: (six.text_type, int, **Tag) -> None
        """
        Construct a counter.

        :param name: The counter name
        :param initial_value: The initial value of this counter, which may be only an integer
        :param tags: The tags associated with this counter (not that not all publishers will support tags)
        """
        if not isinstance(initial_value, six.integer_types) or initial_value < 0:
            raise TypeError('Counter values must be non-null, non-negative integers')

        super(Counter, self).__init__(name, int(initial_value), **tags)

    def increment(self, amount=1):  # type: (int) -> int
        """
        Increments this counter's value by the specified amount.

        :param amount: The amount by which to increment the counter, defaults to 1

        :return: The new value
        """
        self._value += amount
        return self.value

    def reset(self, value=None):  # type: (Optional[int]) -> int
        """
        Resets this counter to the specified value or the initial value if not specified.

        :param value: The value to which to reset this counter, which defaults to the initial value if not specified

        :return: The new value
        """
        if value is None:
            self._value = self._initial_value
        else:
            if value < 0:
                raise ValueError('Counters allow only non-negative integers')
            self._value = int(value)
        return self.value

    @property
    def value(self):  # type: () -> int
        """
        Returns the value of this counter.

        :return: The counter value
        """
        return int(self._value)

    def record_over_function(self, f, *args, **kwargs):  # type: (Callable[..., R], *Any, **Any) -> R
        """
        Increments this counter and then calls the specified callable with the specified positional and keyword
        arguments.

        :param f: The callable to invoke
        :param args: The positional arguments to pass to the callable
        :param kwargs: The keyword arguments to pass to the callable

        :return: The value the callable returns, unaltered
        """
        self.increment()
        return f(*args, **kwargs)


class Histogram(Metric):
    """
    A histogram is a metric for tracking an arbitrary number of something per named activity.
    """

    def set(self, value=None):  # type: (Optional[Union[int, float]]) -> int
        """
        Sets this histogram to the specified value or the initial value if not specified.

        :param value: The value to which to set this histogram, which defaults to the initial value if not specified

        :return: The new value
        """
        if value is None:
            self._value = self._initial_value
        else:
            if value < 0:
                raise ValueError('Histograms allow only non-negative values')
            self._value = value
        return self.value if self.value is not None else 0  # actually not possible to be None here, but satisfy MyPy


class TimerResolution(enum.IntEnum):
    """
    An enum controlling the resolution of published timer values.
    """

    MILLISECONDS = 10**3
    """The timer value will be multiplied by 1,000 and then rounded to an integer before publication"""

    MICROSECONDS = 10**6
    """The timer value will be multiplied by 1,000,000 and then rounded to an integer before publication"""

    NANOSECONDS = 10**9
    """The timer value will be multiplied by 1,000,000,000 and then rounded to an integer before publication"""


class Timer(Histogram):
    """
    A timer is simply a specialized histogram that tracks the arbitrary number of milliseconds, microseconds, or
    nanoseconds per named activity. A single timer instance can be restarted and re-stopped repeatedly, and its value
    will accumulate/increase by the elapsed time each time the timer is stopped. Only if the timer has never been
    started and stopped will the initial or set value be used for publication.
    """

    def __init__(self, name, initial_value=0, resolution=TimerResolution.MILLISECONDS, **tags):
        # type: (six.text_type, Union[int, float], TimerResolution, **Tag) -> None
        """
        Construct a timer.

        :param name: The timer name
        :param initial_value: The initial value of this timer, which may be an integer or a float (which will be
                              rounded)
        :param resolution: The resolution of this timer, which if unset defaults to milliseconds, controls how the
                           value is published (it is multiplied by the resolution factor and then rounded to an
                           integer). It does not affect the initial value, only the value recorded with `start` /
                           `stop` and context manager usage
        :param tags: The tags associated with this timer (not that not all publishers will support tags)
        """
        super(Timer, self).__init__(name, initial_value, **tags)

        self._start_time = None  # type: Optional[float]
        self._running_value = 0.0

        if self._initial_value and self._initial_value > 0:
            self._value = self._initial_value

        self.resolution = resolution

        self.start()

    def start(self):  # type: () -> None
        """
        Starts the timer.
        """
        self._start_time = time.time()

    def stop(self):  # type: () -> None
        """
        Stops the timer.
        """
        if self._start_time is None:
            return  # Cannot stop a timer before it has started
        self._running_value += time.time() - self._start_time
        self._start_time = None

    @property
    def value(self):  # type: () -> Optional[int]
        """
        If the timer has been started and stopped, this returns the total elapsed time of the timer multiplied by the
        resolution and rounded to an integer. Otherwise, this returns the set or initial value of the timer, not
        multiplied, but rounded to an integer.

        :return: The timer value
        """
        if self._running_value > 0 and not self._start_time:
            # If the timer is not currently running but it has previously run, return that amount times the resolution
            # noinspection PyTypeChecker
            return int(round(self._running_value * self.resolution))

        if self._value:
            # Set from initial value, assume the resolution was already correct
            return int(round(float(self._value)))

        return None

    def __enter__(self):  # type: () -> Timer
        """
        Starts the timer at the start of a `with` block.

        :return: `self`
        """
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):  # type: (Any, Any, Any) -> Literal[False]
        """
        Stops the timer at the end of a `with` block, regardless of whether an exception occurred.

        :param exc_type: Ignored
        :param exc_value: Ignored
        :param traceback: Ignored

        :return: `False`
        """
        self.stop()
        # noinspection PyTypeChecker
        return False

    def record_over_function(self, f, *args, **kwargs):  # type: (Callable[..., R], *Any, **Any) -> R
        """
        Starts this timer, calls the specified callable with the specified positional and keyword arguments, and then
        stops this timer.

        :param f: The callable to invoke
        :param args: The positional arguments to pass to the callable
        :param kwargs: The keyword arguments to pass to the callable

        :return: The value the callable returns, unaltered
        """
        with self:
            return f(*args, **kwargs)


class Gauge(Metric):
    """
    A gauge is a metric for tracking the ongoing state of something, such as number of items waiting in a queue, size
    of a database or file system, etc.
    """

    def __init__(self, name, initial_value=0, **tags):  # type: (six.text_type, int, **Tag) -> None
        """
        Construct a gauge.

        :param name: The gauge name
        :param initial_value: The initial value of this gauge, which may be an integer
        :param tags: The tags associated with this gauge (not that not all publishers will support tags)
        """
        if not isinstance(initial_value, six.integer_types) or initial_value < 0:
            raise TypeError('Gauge values must be non-null, non-negative integers')

        super(Gauge, self).__init__(name, initial_value, **tags)

    def set(self, value=None):  # type: (Optional[int]) -> int
        """
        Sets this gauge to the specified value or the initial value if not specified.

        :param value: The value to which to set this gauge, which defaults to the initial value if not specified

        :return: The new value
        """
        if value is None:
            self._value = self._initial_value
        else:
            if value < 0:
                raise ValueError('Gauges allow only non-negative integers')
            self._value = value
        return self.value if self.value is not None else 0  # actually not possible to be None here, but satisfy MyPy
