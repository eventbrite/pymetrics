from __future__ import (
    absolute_import,
    unicode_literals,
)

import copy
import time
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
)

from pymetrics.instruments import (
    Counter,
    Gauge,
    Histogram,
    Metric,
    Timer,
    TimerResolution,
)
from pymetrics.recorders.base import MetricsRecorder


M = TypeVar("M", bound=Metric)


class DefaultMetricsRecorder(MetricsRecorder):
    """
    Default implementation of a metrics recorder.
    """

    def __init__(self, prefix=None, meta=False):
        # type: (Optional[str], bool) -> None
        """
        Initialize the recorder.

        :param prefix: Optional prefix for all metric names
        :param meta: Whether to record meta-metrics
        """
        self.prefix = prefix
        self.meta = meta
        self.counters = {}  # type: Dict[str, Counter]
        self.histograms = {}  # type: Dict[str, List[Histogram]]
        self.timers = {}  # type: Dict[str, List[Timer]]
        self.gauges = {}  # type: Dict[str, List[Gauge]]
        self._last_publish_time = 0

    def _get_metric_name(self, name):
        # type: (str) -> str
        """
        Get the full metric name with prefix.

        :param name: The base metric name
        :return: The full metric name
        """
        if self.prefix:
            return f"{self.prefix}.{name}"
        return name

    def _get_metric_key(self, name, tags):
        # type: (str, Dict[str, Any]) -> str
        """
        Get a unique key for a metric based on name and tags.

        :param name: The metric name
        :param tags: The metric tags
        :return: A unique key
        """
        if not tags:
            return name

        # Sort tags for consistent key generation
        sorted_tags = sorted(tags.items())
        tag_str = ",".join(f"{k}={v}" for k, v in sorted_tags)
        return f"{name}:{tag_str}"

    def _get_or_create_metrics(self, original, name, force_new, metric_type, initial_value, **tags):
        # type: (Dict[str, List[M]], str, bool, Type[M], int, **Any) -> M
        """
        Get or create a metric of the specified type.

        :param original: The original metrics dictionary
        :param name: The metric name
        :param force_new: Whether to force creation of a new metric
        :param metric_type: The type of metric to create
        :param initial_value: The initial value
        :param tags: Additional tags
        :return: The metric instance
        """
        key = self._get_metric_key(name, tags)

        if key not in original or force_new:
            metric = metric_type(name, initial_value, **tags)
            if key not in original:
                original[key] = []
            original[key].append(metric)
            return metric

        return original[key][-1]

    def record_counter(self, name, value=1, **tags):
        # type: (str, int, **Tag) -> Counter
        """
        Record a counter metric.

        :param name: The name of the counter
        :param value: The value to increment by
        :param tags: Additional tags for the counter

        :return: The counter instance
        """
        full_name = self._get_metric_name(name)
        key = self._get_metric_key(full_name, tags)

        if key not in self.counters:
            self.counters[key] = Counter(full_name, 0, **tags)

        counter = self.counters[key]
        counter.increment(value)
        return counter

    def record_histogram(self, name, value, **tags):
        # type: (str, bool, int, **Tag) -> Histogram
        """
        Record a histogram metric.

        :param name: The name of the histogram
        :param value: The value to record
        :param tags: Additional tags for the histogram

        :return: The histogram instance
        """
        full_name = self._get_metric_name(name)
        histogram = self._get_or_create_metrics(self.histograms, full_name, False, Histogram, 0, **tags)
        histogram.set(value)
        return histogram

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
        full_name = self._get_metric_name(name)
        if resolution is None:
            resolution = TimerResolution.MILLISECONDS

        timer = self._get_or_create_metrics(self.timers, full_name, False, Timer, 0, resolution=resolution, **tags)
        timer.set(value)
        return timer

    def record_gauge(self, name, value, **tags):
        # type: (str, bool, int, **Tag) -> Gauge
        """
        Record a gauge metric.

        :param name: The name of the gauge
        :param value: The value to set
        :param tags: Additional tags for the gauge

        :return: The gauge instance
        """
        full_name = self._get_metric_name(name)
        gauge = self._get_or_create_metrics(self.gauges, full_name, False, Gauge, 0, **tags)
        gauge.set(value)
        return gauge

    def get_metrics(self):
        # type: () -> List[Metric]
        """
        Get all recorded metrics.

        :return: A list of all metrics
        """
        metrics = []
        metrics.extend(self.counters.values())
        metrics.extend(gauge for gauges in self.gauges.values() for gauge in gauges if gauge.value is not None)
        metrics.extend(
            histogram
            for histograms in self.histograms.values()
            for histogram in histograms
            if histogram.value is not None
        )
        metrics.extend(timer for timers in self.timers.values() for timer in timers if timer.value is not None)
        return metrics

    def publish_all(self):
        # type: () -> None
        """
        Publish all metrics and clear them.
        """
        self._last_publish_time = time.time()
        # Clear all metrics after publishing
        self.counters.clear()
        self.histograms.clear()
        self.timers.clear()
        self.gauges.clear()

    def configure(self, config=None):
        # type: (Optional[Dict[str, Any]]) -> None
        """
        Configure this recorder.

        :param config: The configuration dictionary
        """
        if config:
            self.prefix = config.get("prefix", self.prefix)
            self.meta = config.get("meta", self.meta)

    @classmethod
    def get_config_from_django(cls):
        # type: () -> Optional[Dict[str, Any]]
        """
        Get configuration from Django settings.

        :return: Configuration dictionary or None
        """
        try:
            from django.conf import settings

            return {
                "prefix": getattr(settings, "PYMETRICS_PREFIX", None),
                "meta": getattr(settings, "PYMETRICS_META", False),
            }
        except ImportError:
            return None


def _recorder(prefix, meta=False):
    # type: (Optional[str], bool) -> DefaultMetricsRecorder
    """
    Create a recorder instance.

    :param prefix: Optional prefix for metric names
    :param meta: Whether to record meta-metrics
    :return: A recorder instance
    """
    return DefaultMetricsRecorder(prefix=prefix, meta=meta)
