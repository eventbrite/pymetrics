from __future__ import (
    absolute_import,
    unicode_literals,
)

import six  # noqa: F401 TODO Python 3

from pymetrics.instruments import (  # noqa: F401 TODO Python 3
    Counter,
    Gauge,
    Histogram,
    Tag,
    Timer,
    TimerResolution,
)
from pymetrics.recorders.base import MetricsRecorder


__all__ = (
    'NonOperationalMetricsRecorder',
    'noop_metrics',
)


class NonOperationalMetricsRecorder(MetricsRecorder):
    """
    A special metrics recorder that ignores configuration and doesn't keep track of or publish any metrics, useful for
    testing and defaulting a metrics variable to eliminate conditional metrics recording.
    """

    def counter(self, name, initial_value=0, **tags):
        # type: (six.text_type, int, **Tag) -> Counter
        return Counter(name, initial_value, **tags)

    def histogram(self, name, force_new=False, initial_value=0, **tags):
        # type: (six.text_type, bool, int, **Tag) -> Histogram
        return Histogram(name, initial_value, **tags)

    def timer(self, name, force_new=False, resolution=TimerResolution.MILLISECONDS, initial_value=0, **tags):
        # type: (six.text_type, bool, TimerResolution, int, **Tag) -> Timer
        return Timer(name, initial_value, resolution, **tags)

    def gauge(self, name, force_new=False, initial_value=0, **tags):
        # type: (six.text_type, bool, int, **Tag) -> Gauge
        return Gauge(name, initial_value, **tags)

    def publish_all(self):
        # type: () -> None
        """Does nothing"""

    def publish_if_full_or_old(self, max_metrics=18, max_age=10):
        # type: (int, int) -> None
        """Does nothing"""

    def throttled_publish_all(self, delay=10):
        # type: (int) -> None
        """Does nothing"""

    def clear(self, only_published=False):
        # type: (bool) -> None
        """Does nothing"""


noop_metrics = NonOperationalMetricsRecorder()
"""A singleton instance of `NonOperationalMetricsRecorder`."""
