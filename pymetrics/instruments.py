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


try:
    from typing import Literal  # type: ignore
except ImportError:
    from typing_extensions import Literal  # type: ignore


__all__ = (
    "Counter",
    "Gauge",
    "Histogram",
    "Metric",
    "Tag",
    "Timer",
    "TimerResolution",
)


R = TypeVar("R")

Tag = Union[str, bytes, int, float, bool, None]


_valid_initial_values = (int, float)  # type: Tuple[Type, ...]


class Metric(object):
    """
    A base metric instrument from which all metric instruments inherit. Cannot be instantiated directly.
    """

    def __init__(self, name, initial_value=0, **tags):
        # type: (str, Union[int, float], **Tag) -> None
        """
        Construct a metric.

        :param name: The metric name
        :param initial_value: The initial value of this metric, which may be an integer or a float (which will be
                              rounded)
        :param tags: The tags associated with this metric (not that not all publishers will support tags)
        """
        if self.__class__ == Metric:
            raise TypeError('Cannot instantiate abstract class "Metric"')
        if not isinstance(name, str):
            raise TypeError("Metric names must be non-null strings")
        if not isinstance(initial_value, _valid_initial_values):
            raise TypeError("Metric values must be integers or floats")

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
        raise TypeError("{}s do not support use as a decorator".format(self.__class__.__name__))

    def __repr__(self):
        return '{}(name="{}", value={})'.format(self.__class__.__name__, self.name, self.value)


class Counter(Metric):
    """
    A counter metric that can only be incremented. Cannot be decremented or reset to a value less than the current
    value.
    """

    def __init__(self, name, initial_value=0, **tags):  # type: (str, int, **Tag) -> None
        """
        Construct a counter.

        :param name: The metric name
        :param initial_value: The initial value of this counter, which must be a non-negative integer
        :param tags: The tags associated with this metric
        """
        if not isinstance(initial_value, int) or initial_value < 0:
            raise TypeError("Counter initial values must be non-negative integers")
        super(Counter, self).__init__(name, initial_value, **tags)

    def increment(self, amount=1):  # type: (int) -> int
        """
        Increment this counter by the specified amount.

        :param amount: The amount to increment by (must be positive)

        :return: The new value of this counter
        """
        if amount <= 0:
            raise ValueError("Counter increments must be positive")
        self._value += amount
        return self.value

    def reset(self, value=None):  # type: (Optional[int]) -> int
        """
        Reset this counter to the specified value, or to its initial value if no value is specified.

        :param value: The value to reset to (must be non-negative)

        :return: The new value of this counter
        """
        if value is not None:
            if not isinstance(value, int) or value < 0:
                raise TypeError("Counter values must be non-negative integers")
            self._value = value
        else:
            self._value = self._initial_value
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
        Records this counter around calling the specified callable with the specified positional and keyword arguments.
        The counter is incremented by 1 before the callable is invoked.

        :param f: The callable to invoke
        :param args: The positional arguments to pass to the callable
        :param kwargs: The keyword arguments to pass to the callable

        :return: The value the callable returns, unaltered
        """
        self.increment()
        return f(*args, **kwargs)


class Histogram(Metric):
    """
    A histogram metric that tracks the distribution of values.
    """

    def set(self, value=None):  # type: (Optional[Union[int, float]]) -> int
        """
        Set the value of this histogram.

        :param value: The value to set (if None, the histogram is reset to its initial value)

        :return: The new value of this histogram
        """
        if value is None:
            self._value = self._initial_value
        else:
            if not isinstance(value, _valid_initial_values):
                raise TypeError("Histogram values must be integers or floats")
            self._value = value
        return self.value


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
    A timer metric that tracks the duration of operations.
    """

    def __init__(self, name, initial_value=0, resolution=TimerResolution.MILLISECONDS, **tags):
        # type: (str, Union[int, float], TimerResolution, **Tag) -> None
        """
        Construct a timer.

        :param name: The metric name
        :param initial_value: The initial value of this timer, which must be a non-negative number
        :param resolution: The resolution to use when publishing this timer
        :param tags: The tags associated with this metric
        """
        if not isinstance(initial_value, _valid_initial_values) or initial_value < 0:
            raise TypeError("Timer initial values must be non-negative numbers")
        if not isinstance(resolution, TimerResolution):
            raise TypeError("Timer resolution must be a TimerResolution enum value")
        super(Timer, self).__init__(name, initial_value, **tags)
        self._resolution = resolution
        self._start_time = None

    def start(self):  # type: () -> None
        """
        Start timing an operation.
        """
        self._start_time = time.time()

    def stop(self):  # type: () -> None
        """
        Stop timing an operation and record the elapsed time.
        """
        if self._start_time is None:
            raise RuntimeError("Timer was not started")
        elapsed = time.time() - self._start_time
        self.set(elapsed)
        self._start_time = None

    @property
    def value(self):  # type: () -> Optional[int]
        """
        Returns the value of this timer, converted to the specified resolution.

        :return: The timer value in the specified resolution
        """
        if self._value is None:
            return None
        return int(round(float(self._value) * self._resolution))

    def __enter__(self):  # type: () -> Timer
        """
        Context manager entry point.

        :return: This timer
        """
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):  # type: (Any, Any, Any) -> Literal[False]
        """
        Context manager exit point.

        :param exc_type: The exception type (if any)
        :param exc_value: The exception value (if any)
        :param traceback: The traceback (if any)

        :return: False to allow exceptions to propagate
        """
        self.stop()
        return False

    def record_over_function(self, f, *args, **kwargs):  # type: (Callable[..., R], *Any, **Any) -> R
        """
        Records this timer around calling the specified callable with the specified positional and keyword arguments.

        :param f: The callable to invoke
        :param args: The positional arguments to pass to the callable
        :param kwargs: The keyword arguments to pass to the callable

        :return: The value the callable returns, unaltered
        """
        with self:
            return f(*args, **kwargs)


class Gauge(Metric):
    """
    A gauge metric that can be set to any value.
    """

    def __init__(self, name, initial_value=0, **tags):  # type: (str, int, **Tag) -> None
        """
        Construct a gauge.

        :param name: The metric name
        :param initial_value: The initial value of this gauge, which must be a non-negative integer
        :param tags: The tags associated with this metric
        """
        if not isinstance(initial_value, int) or initial_value < 0:
            raise TypeError("Gauge initial values must be non-negative integers")
        super(Gauge, self).__init__(name, initial_value, **tags)

    def set(self, value=None):  # type: (Optional[int]) -> int
        """
        Set the value of this gauge.

        :param value: The value to set (if None, the gauge is reset to its initial value)

        :return: The new value of this gauge
        """
        if value is None:
            self._value = self._initial_value
        else:
            if not isinstance(value, int) or value < 0:
                raise TypeError("Gauge values must be non-negative integers")
            self._value = value
        return self.value
