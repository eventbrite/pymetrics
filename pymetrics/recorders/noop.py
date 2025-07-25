from typing import List

from pymetrics.instruments import Counter, Gauge, Histogram, Metric, Timer, TimerResolution
from pymetrics.recorders.base import MetricsRecorder


class NoopMetricsRecorder(MetricsRecorder):
    """
    A no-op implementation of a metrics recorder that does nothing.
    """

    def record_counter(self, name, value=1, **tags):
        # type: (str, int, **Tag) -> Counter
        """
        Record a counter metric (no-op).

        :param name: The name of the counter
        :param value: The value to increment by
        :param tags: Additional tags for the counter

        :return: A dummy counter instance
        """
        return Counter(name, 0, **tags)

    def record_histogram(self, name, value, **tags):
        # type: (str, bool, int, **Tag) -> Histogram
        """
        Record a histogram metric (no-op).

        :param name: The name of the histogram
        :param value: The value to record
        :param tags: Additional tags for the histogram

        :return: A dummy histogram instance
        """
        return Histogram(name, 0, **tags)

    def record_timer(self, name, value, resolution=None, **tags):
        # type: (str, bool, TimerResolution, int, **Tag) -> Timer
        """
        Record a timer metric (no-op).

        :param name: The name of the timer
        :param value: The value to record
        :param resolution: The resolution to use
        :param tags: Additional tags for the timer

        :return: A dummy timer instance
        """
        if resolution is None:
            resolution = TimerResolution.MILLISECONDS
        return Timer(name, 0, resolution, **tags)

    def record_gauge(self, name, value, **tags):
        # type: (str, bool, int, **Tag) -> Gauge
        """
        Record a gauge metric (no-op).

        :param name: The name of the gauge
        :param value: The value to set
        :param tags: Additional tags for the gauge

        :return: A dummy gauge instance
        """
        return Gauge(name, 0, **tags)

    def get_metrics(self):
        # type: () -> List[Metric]
        """
        Get all recorded metrics (always empty for no-op recorder).

        :return: An empty list
        """
        return []
