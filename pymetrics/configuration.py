from __future__ import (
    absolute_import,
    unicode_literals,
)

import logging
from typing import (
    Any,
    Dict,
    Optional,
)

import attr

from pymetrics.publishers.base import MetricsPublisher
from pymetrics.recorders.base import MetricsRecorder


@attr.s
class Configuration(object):
    """Configuration for the metrics system."""

    recorder = attr.ib()  # type: MetricsRecorder
    publishers = attr.ib(default=attr.Factory(list))  # type: list[MetricsPublisher]
    error_logger_name = attr.ib(default=None)  # type: Optional[str]

    def __attrs_post_init__(self):
        """Post-initialization hook."""
        if self.error_logger_name:
            self._error_logger = logging.getLogger(self.error_logger_name)
        else:
            self._error_logger = None

    def record_counter(self, name, value=1, **tags):
        """Record a counter metric."""
        try:
            self.recorder.record_counter(name, value, **tags)
        except Exception as e:
            if self._error_logger:
                self._error_logger.error("Failed to record counter %s: %s", name, e)

    def record_histogram(self, name, value, **tags):
        """Record a histogram metric."""
        try:
            self.recorder.record_histogram(name, value, **tags)
        except Exception as e:
            if self._error_logger:
                self._error_logger.error("Failed to record histogram %s: %s", name, e)

    def record_timer(self, name, value, resolution=None, **tags):
        """Record a timer metric."""
        try:
            self.recorder.record_timer(name, value, resolution, **tags)
        except Exception as e:
            if self._error_logger:
                self._error_logger.error("Failed to record timer %s: %s", name, e)

    def record_gauge(self, name, value, **tags):
        """Record a gauge metric."""
        try:
            self.recorder.record_gauge(name, value, **tags)
        except Exception as e:
            if self._error_logger:
                self._error_logger.error("Failed to record gauge %s: %s", name, e)

    def publish(self, flush=True):
        """Publish all metrics to all publishers."""
        try:
            metrics = self.recorder.get_metrics()
            for publisher in self.publishers:
                publisher.publish(metrics, flush)
        except Exception as e:
            if self._error_logger:
                self._error_logger.error("Failed to publish metrics: %s", e)


def create_configuration(config_dict):
    # type: (Dict[str, Any]) -> Configuration
    """Create a configuration from a dictionary."""
    # This is a placeholder for the actual implementation
    # which would parse the config_dict and create the appropriate
    # recorder and publishers
    raise NotImplementedError("Configuration creation from dict not yet implemented")
