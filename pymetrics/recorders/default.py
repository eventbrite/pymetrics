from __future__ import (
    absolute_import,
    unicode_literals,
)

import time
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from conformity import fields
from conformity.error import ValidationError
import six

from pymetrics.configuration import (
    CONFIGURATION_SCHEMA,
    Configuration,
    create_configuration,
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
from pymetrics.publishers.utils import publish_metrics
from pymetrics.recorders.base import MetricsRecorder


__all__ = (
    'DefaultMetricsRecorder',
)


M = TypeVar('M', bound=Metric)


@fields.ClassConfigurationSchema.provider(fields.Dictionary(
    {
        'prefix': fields.Nullable(fields.UnicodeString(
            description='An optional prefix for all metrics names (the period delimiter will be added for you)',
        )),
        'config': fields.Nullable(CONFIGURATION_SCHEMA),
    },
    allow_extra_keys=False,
    optional_keys=('config', ),
    description='The configuration schema for the default metrics recorder constructor arguments. Without the '
                '`config` key, it will not be able publish metrics.',
))
class DefaultMetricsRecorder(MetricsRecorder):
    def __init__(self, prefix, config=None):
        # type: (Optional[six.text_type], Optional[Dict[six.text_type, Any]]) -> None
        """
        Construct a new recorder.

        :param prefix: A nullable prefix, which if non-null will be prepended to all metrics names, with a single
                       period separating the prefix and the metrics name.
        :param config: The configuration dictionary complying with the official PyMetrics Conformity configuration
                       schema.
        """
        self.prefix = prefix
        self.counters = {}  # type: Dict[six.text_type, Counter]
        self.histograms = {}  # type: Dict[six.text_type, List[Histogram]]
        self.timers = {}  # type: Dict[six.text_type, List[Timer]]
        self.gauges = {}  # type: Dict[six.text_type, List[Gauge]]
        self.unpublished_metrics_count = 0  # type: int
        self._last_publish_timestamp = 0  # type: float

        self._configuration = None  # type: Optional[Configuration]
        self.configure(config)

    @property
    def is_configured(self):  # type: () -> bool
        return self._configuration is not None

    def clear(self, only_published=False):  # type: (bool) -> None
        remaining_histograms = 0
        remaining_timers = 0

        self.counters = {}
        if only_published:
            self.histograms, remaining_histograms = self._get_metric_dict_cleared_of_published_metrics(self.histograms)
            self.timers, remaining_timers = self._get_metric_dict_cleared_of_published_metrics(self.timers)
        else:
            self.histograms = {}
            self.timers = {}
        self.gauges = {}
        self.unpublished_metrics_count = remaining_histograms + remaining_timers

    @staticmethod
    def _get_metric_dict_cleared_of_published_metrics(original):
        # type: (Dict[six.text_type, List[M]]) -> Tuple[Dict[six.text_type, List[M]], int]
        if not original:
            return {}, 0

        new = {}
        remaining = 0
        for name, metrics in six.iteritems(original):
            new_metrics = [metric for metric in metrics if metric.value is None]
            if new_metrics:
                new[name] = new_metrics
                remaining += len(new_metrics)
        return new, remaining

    def _get_name(self, name, other_concerns):
        # type: (six.text_type, Dict[Union[str, six.text_type], Any]) -> Tuple[six.text_type, six.text_type]
        if self.prefix:
            name = '.'.join((self.prefix, name))
        internal_name = name
        if other_concerns and ('resolution' not in other_concerns or len(other_concerns) > 1):
            internal_name += '#{}'.format(str(hash(frozenset(
                (k, v) for k, v in six.iteritems(other_concerns) if k != 'resolution'
            ))))
        return name, internal_name

    def counter(self, name, initial_value=0, **tags):
        # type: (six.text_type, int, **Tag) -> Counter
        name, internal_name = self._get_name(name, tags)

        if internal_name not in self.counters:
            self.counters[internal_name] = Counter(name, initial_value=initial_value, **tags)
            self.unpublished_metrics_count += 1

        return self.counters[internal_name]

    def _get_metric_from_list_or_create(self, collection, name, force_new, metric, initial_value, **kwargs):
        # type: (Dict[six.text_type, List[M]], six.text_type, bool, Type[M], int, **Any) -> M
        name, internal_name = self._get_name(name, kwargs)

        if internal_name not in collection:
            collection[internal_name] = [metric(name, initial_value=initial_value, **kwargs)]
            self.unpublished_metrics_count += 1

        elif force_new or collection[internal_name][-1].value is not None:
            collection[internal_name].append(metric(name, initial_value=initial_value, **kwargs))
            self.unpublished_metrics_count += 1

        return collection[internal_name][-1]

    def histogram(self, name, force_new=False, initial_value=0, **tags):
        # type: (six.text_type, bool, int, **Tag) -> Histogram
        return self._get_metric_from_list_or_create(self.histograms, name, force_new, Histogram, initial_value, **tags)

    def timer(self, name, force_new=False, resolution=TimerResolution.MILLISECONDS, initial_value=0, **tags):
        # type: (six.text_type, bool, TimerResolution, int, **Tag) -> Timer
        return self._get_metric_from_list_or_create(
            self.timers,
            name,
            force_new,
            Timer,
            initial_value,
            resolution=resolution,
            **tags
        )

    def gauge(self, name, force_new=False, initial_value=0, **tags):
        # type: (six.text_type, bool, int, **Tag) -> Gauge
        return self._get_metric_from_list_or_create(self.gauges, name, force_new, Gauge, initial_value, **tags)

    def get_all_metrics(self):  # type: () -> List[Metric]
        meta_timer = None
        if self._configuration and self._configuration.enable_meta_metrics is True:
            meta_timer = Timer('pymetrics.meta.recorder.get_all_metrics', resolution=TimerResolution.MICROSECONDS)

        metrics = []  # type: List[Metric]
        metrics.extend(six.itervalues(self.counters))
        metrics.extend(gauge for gauges in six.itervalues(self.gauges) for gauge in gauges if gauge.value is not None)
        metrics.extend(
            histogram
            for histograms in six.itervalues(self.histograms) for histogram in histograms if histogram.value is not None
        )
        metrics.extend(timer for timers in six.itervalues(self.timers) for timer in timers if timer.value is not None)

        if meta_timer:
            meta_timer.stop()
            metrics.insert(0, meta_timer)

        return metrics

    def configure(self, config=None):  # type: (Optional[Dict[six.text_type, Any]]) -> None
        if not self._configuration:
            # If this recorder is not yet configured
            configuration = None  # type: Optional[Configuration]
            if config:
                # If a local configuration was passed in, use it
                configuration = create_configuration(config)
            else:
                # Attempt to get configuration settings from Django, if available
                config = self.get_config_from_django()
                if config:
                    configuration = create_configuration(config)

            self._configuration = configuration

    # noinspection PyUnresolvedReferences
    @classmethod
    def get_config_from_django(cls):  # type: () -> Optional[Dict[six.text_type, Any]]
        """
        When not in Django context, this is a no-op, returning None. Otherwise, it attempts to return the `METRICS`
        setting from Django settings, if it exists, or the `metrics` setting from the `SOA_SERVER_SETTINGS` setting
        from Django settings, if it exists. `METRICS` is a standard established by this library. `SOA_SERVER_SETTINGS`
        is a standard established in PySOA, which uses PyMetrics.

        :return: The configuration dict from Django settings, if it exists, or None
        """
        settings = cls.get_django_settings()
        if settings:
            if getattr(settings, 'METRICS', None):
                return settings.METRICS
            elif getattr(settings, 'SOA_SERVER_SETTINGS', None):
                return settings.SOA_SERVER_SETTINGS['metrics']['kwargs']['config']

        return None

    class StubImproperlyConfigured(Exception):
        """A stub exception in case Django can't be imported."""

    DjangoImproperlyConfigured = StubImproperlyConfigured
    django_settings = None
    attempted_django_exception_import = False

    # noinspection PyUnresolvedReferences,PyPackageRequirements
    @classmethod
    def get_django_settings(cls):
        if not cls.attempted_django_exception_import:
            # Only attempt to import Django a single time; if it can't be imported once, it'll never import successfully
            cls.attempted_django_exception_import = True
            try:
                from django.core.exceptions import ImproperlyConfigured
                cls.DjangoImproperlyConfigured = ImproperlyConfigured
            except ImportError:
                pass

        if not cls.django_settings and cls.DjangoImproperlyConfigured is not cls.StubImproperlyConfigured:
            # If the settings haven't been imported yet, but we do have the real Django exception, keep trying to
            # import settings, in case they're improperly configured initially but aren't later.
            try:
                from django.conf import settings
                if settings:
                    # Django won't actually raise ImproperlyConfigured unless you try to _use_ the settings.
                    getattr(settings, 'DEBUG', False)
                    cls.django_settings = settings
            except (ImportError, cls.DjangoImproperlyConfigured):
                # Could be a circular import or problem with settings that might be resolved at a later time.
                pass
            except ValidationError as e:
                # Likely a circular import that will be resolved at a later time.
                if not (e.args[0] and 'ImportError: ' in e.args[0]):
                    raise

        return cls.django_settings

    def publish_all(self):  # type: () -> None
        if self._configuration:
            metrics = self.get_all_metrics()
            publish_metrics(metrics, self._configuration)
        # silently ignoring situation when not configured, otherwise we'd spam logging
        # clear all regardless if we send, don't want to hog the memory
        self.clear(only_published=True)
        self._last_publish_timestamp = time.time()

    def publish_if_full_or_old(self, max_metrics=18, max_age=10):  # type: (int, int) -> None
        if self.unpublished_metrics_count > max_metrics or time.time() - self._last_publish_timestamp >= max_age:
            self.publish_all()

    def throttled_publish_all(self, delay=10):  # type: (int) -> None
        if time.time() - self._last_publish_timestamp >= delay:
            self.publish_all()
