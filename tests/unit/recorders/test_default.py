from __future__ import (
    absolute_import,
    unicode_literals,
)

import time
from typing import (
    Any,
    Dict,
    Optional,
    cast,
)

from conformity import fields
from conformity.error import ValidationError
import freezegun
import mock
import pytest
import six

from pymetrics.instruments import (
    Timer,
    TimerResolution,
)
from pymetrics.publishers.base import MetricsPublisher
from pymetrics.publishers.null import NullPublisher
from pymetrics.recorders.base import MetricsRecorder
from pymetrics.recorders.default import DefaultMetricsRecorder


mock_publisher = mock.MagicMock(spec=MetricsPublisher)
mock_publisher_extra = mock.MagicMock(spec=MetricsPublisher)


# noinspection PyAbstractClass
@fields.ClassConfigurationSchema.provider(
    fields.Dictionary({}),
)
class MockPublisher(MetricsPublisher):
    def __new__(cls, *args, **kwargs):
        return mock_publisher


# noinspection PyAbstractClass
@fields.ClassConfigurationSchema.provider(
    fields.Dictionary({}),
)
class MockPublisherExtra(MetricsPublisher):
    def __new__(cls, *args, **kwargs):
        return mock_publisher_extra


class FakeImproperlyConfigured(Exception):
    pass


# noinspection PyProtectedMember
class TestDefaultMetricsRecorderConfiguration(object):
    # noinspection PyMethodMayBeStatic
    def teardown_method(self, _method):
        DefaultMetricsRecorder.attempted_django_exception_import = False
        DefaultMetricsRecorder.django_settings = None
        DefaultMetricsRecorder.DjangoImproperlyConfigured = DefaultMetricsRecorder.StubImproperlyConfigured

    def test_config_no_config(self):
        recorder = DefaultMetricsRecorder('me')
        assert recorder.is_configured is False

    def test_config_explicit(self):
        recorder = DefaultMetricsRecorder('me', config={
            'version': 2,
            'publishers': [
                {'path': 'tests.unit.recorders.test_default:MockPublisher'},
            ],
        })
        assert recorder.is_configured is True

        assert recorder._configuration is not None
        assert len(recorder._configuration.publishers) == 1
        assert recorder._configuration.publishers[0] is mock_publisher

        # re-config should do nothing
        recorder.configure({'bad_config': 'bad_value'})

    def test_config_django_causes_conformity_import_error(self):
        django_exceptions = mock.MagicMock()
        django_exceptions.ImproperlyConfigured = FakeImproperlyConfigured

        django_conf = mock.MagicMock()
        e = ValidationError(
            "Invalid keyword arguments:\n  - middleware.0.path: ImportError: cannot import name 'baz' from 'foo.bar' "
        )
        if six.PY2:
            django_conf.settings.__nonzero__.side_effect = e
        else:
            django_conf.settings.__bool__.side_effect = e

        with mock.patch.dict('sys.modules', {
            'django': mock.MagicMock(),
            'django.conf': django_conf,
            'django.core': mock.MagicMock(),
            'django.core.exceptions': django_exceptions,
        }):
            recorder = DefaultMetricsRecorder('me')

        assert recorder.is_configured is False

    def test_config_django_causes_conformity_other_error(self):
        django_exceptions = mock.MagicMock()
        django_exceptions.ImproperlyConfigured = FakeImproperlyConfigured

        django_conf = mock.MagicMock()
        e = ValidationError(
            "Invalid keyword arguments:\n  - middleware.0.path: Some other error that isn't an import error "
        )
        if six.PY2:
            django_conf.settings.__nonzero__.side_effect = e
        else:
            django_conf.settings.__bool__.side_effect = e

        with mock.patch.dict('sys.modules', {
            'django': mock.MagicMock(),
            'django.conf': django_conf,
            'django.core': mock.MagicMock(),
            'django.core.exceptions': django_exceptions,
        }), pytest.raises(ValidationError) as error_context:
            DefaultMetricsRecorder('me')

        assert error_context.value is e

    def test_config_django_available_but_settings_broken1(self):
        django_exceptions = mock.MagicMock()
        django_exceptions.ImproperlyConfigured = FakeImproperlyConfigured

        django_conf = mock.MagicMock()
        if six.PY2:
            django_conf.settings.__nonzero__.side_effect = FakeImproperlyConfigured
        else:
            django_conf.settings.__bool__.side_effect = FakeImproperlyConfigured

        with mock.patch.dict('sys.modules', {
            'django': mock.MagicMock(),
            'django.conf': django_conf,
            'django.core': mock.MagicMock(),
            'django.core.exceptions': django_exceptions,
        }):
            recorder = DefaultMetricsRecorder('me')

        assert recorder.is_configured is False

    def test_config_django_available_but_settings_false(self):
        django_exceptions = mock.MagicMock()
        django_exceptions.ImproperlyConfigured = FakeImproperlyConfigured

        django_conf = mock.MagicMock()
        if six.PY2:
            django_conf.settings.__nonzero__.return_value = False
        else:
            django_conf.settings.__bool__.return_value = False

        with mock.patch.dict('sys.modules', {
            'django': mock.MagicMock(),
            'django.conf': django_conf,
            'django.core': mock.MagicMock(),
            'django.core.exceptions': django_exceptions,
        }):
            recorder = DefaultMetricsRecorder('me')

        assert recorder.is_configured is False

    def test_config_django_available_but_settings_broken2(self):
        django_exceptions = mock.MagicMock()
        django_exceptions.ImproperlyConfigured = FakeImproperlyConfigured

        class S(object):
            def __getattr__(self, item):
                raise FakeImproperlyConfigured()

        django_conf = mock.MagicMock()
        django_conf.settings = S()

        with mock.patch.dict('sys.modules', {
            'django': mock.MagicMock(),
            'django.conf': django_conf,
            'django.core': mock.MagicMock(),
            'django.core.exceptions': django_exceptions,
        }):
            recorder = DefaultMetricsRecorder('me')

        assert recorder.is_configured is False

    def test_config_django_available_but_settings_missing(self):
        django_exceptions = mock.MagicMock()
        django_exceptions.ImproperlyConfigured = FakeImproperlyConfigured

        django_conf = mock.MagicMock()
        django_conf.settings.DEBUG = True
        del django_conf.settings.METRICS
        del django_conf.settings.SOA_SERVER_SETTINGS

        with mock.patch.dict('sys.modules', {
            'django': mock.MagicMock(),
            'django.conf': django_conf,
            'django.core': mock.MagicMock(),
            'django.core.exceptions': django_exceptions,
        }):
            recorder = DefaultMetricsRecorder('me')

        assert recorder.is_configured is False

    def test_config_django_available_main_settings_preferred(self):
        django_exceptions = mock.MagicMock()
        django_exceptions.ImproperlyConfigured = FakeImproperlyConfigured

        django_conf = mock.MagicMock()
        django_conf.settings.DEBUG = True
        django_conf.settings.METRICS = {
            'version': 2,
            'publishers': [
                {'path': 'tests.unit.recorders.test_default:MockPublisherExtra'},
            ]
        }
        django_conf.settings.SOA_SERVER_SETTINGS = {'metrics': {'kwargs': {'config': {
            'version': 2,
            'publishers': [
                {'path': 'tests.unit.recorders.test_default:MockPublisher'},
            ]
        }}}}

        with mock.patch.dict('sys.modules', {
            'django': mock.MagicMock(),
            'django.conf': django_conf,
            'django.core': mock.MagicMock(),
            'django.core.exceptions': django_exceptions,
        }):
            recorder = DefaultMetricsRecorder('me')

            assert recorder.is_configured is True
            assert recorder._configuration is not None
            assert len(recorder._configuration.publishers) == 1
            assert recorder._configuration.publishers[0] is mock_publisher_extra
            assert recorder._configuration.version == 2

            recorder = DefaultMetricsRecorder('you')

            assert recorder.is_configured is True
            assert recorder._configuration is not None
            assert len(recorder._configuration.publishers) == 1
            assert recorder._configuration.publishers[0] is mock_publisher_extra
            assert recorder._configuration.version == 2

    def test_config_django_available_soa_settings_used(self):
        django_exceptions = mock.MagicMock()
        django_exceptions.ImproperlyConfigured = FakeImproperlyConfigured

        django_conf = mock.MagicMock()
        django_conf.settings.DEBUG = True
        del django_conf.settings.METRICS
        django_conf.settings.SOA_SERVER_SETTINGS = {'metrics': {'kwargs': {'config': {
            'version': 2,
            'publishers': [
                {'path': 'tests.unit.recorders.test_default:MockPublisher'},
            ]
        }}}}

        with mock.patch.dict('sys.modules', {
            'django': mock.MagicMock(),
            'django.conf': django_conf,
            'django.core': mock.MagicMock(),
            'django.core.exceptions': django_exceptions,
        }):
            recorder = DefaultMetricsRecorder('me')

            assert recorder.is_configured is True
            assert recorder._configuration is not None
            assert len(recorder._configuration.publishers) == 1
            assert recorder._configuration.publishers[0] is mock_publisher
            assert recorder._configuration.version == 2

            recorder = DefaultMetricsRecorder('you')

            assert recorder.is_configured is True
            assert recorder._configuration is not None
            assert len(recorder._configuration.publishers) == 1
            assert recorder._configuration.publishers[0] is mock_publisher
            assert recorder._configuration.version == 2


# noinspection PyProtectedMember
class TestConfigurationWithConformity(object):
    def test_no_prefix_no_config(self):
        field = fields.ClassConfigurationSchema(base_class=MetricsRecorder)

        config = {
            'path': 'pymetrics.recorders.default.DefaultMetricsRecorder',
            'kwargs': {},
        }  # type: Dict[six.text_type, Any]
        assert field.errors(config)

        config = {
            'path': 'pymetrics.recorders.default.DefaultMetricsRecorder',
            'kwargs': {
                'prefix': None,
            },
        }
        assert not field.errors(config)

        recorder = config['object'](**config['kwargs'])
        assert isinstance(recorder, DefaultMetricsRecorder)
        assert recorder.prefix is None
        assert recorder._configuration is None

    def test_prefix_no_config(self):
        field = fields.ClassConfigurationSchema(base_class=MetricsRecorder)

        config = {
            'path': 'pymetrics.recorders.default.DefaultMetricsRecorder',
            'kwargs': {
                'prefix': 'hello.world',
            },
        }  # type: Dict[six.text_type, Any]
        assert not field.errors(config)

        recorder = config['object'](**config['kwargs'])
        assert isinstance(recorder, DefaultMetricsRecorder)
        assert recorder.prefix == 'hello.world'
        assert recorder._configuration is None

    def test_prefix_with_config(self):
        field = fields.ClassConfigurationSchema(base_class=MetricsRecorder)

        config = {
            'path': 'pymetrics.recorders.default.DefaultMetricsRecorder',
            'kwargs': {
                'prefix': 'goodbye.mars',
                'config': {
                    'version': 2,
                    'publishers': [
                        {'path': 'pymetrics.publishers.null.NullPublisher'}
                    ],
                },
            },
        }  # type: Dict[six.text_type, Any]
        assert not field.errors(config)

        recorder = config['object'](**config['kwargs'])
        assert isinstance(recorder, DefaultMetricsRecorder)
        assert recorder.prefix == 'goodbye.mars'
        assert recorder._configuration is not None
        assert len(recorder._configuration.publishers) == 1
        assert isinstance(recorder._configuration.publishers[0], NullPublisher)


# noinspection PyProtectedMember
class TestDefaultMetricsRecorder(object):
    @staticmethod
    def _recorder(prefix, meta=False):  # type: (Optional[six.text_type], bool) -> DefaultMetricsRecorder
        return DefaultMetricsRecorder(prefix, config={
            'version': 2,
            'enable_meta_metrics': meta,
            'publishers': [
                {'path': 'tests.unit.recorders.test_default:MockPublisher'},
            ],
        })

    def test_counter(self):
        recorder = self._recorder('me')

        recorder.counter('foo.bar').increment()
        recorder.counter('foo.bar').increment()
        recorder.counter('foo.bar').increment()

        recorder.counter('foo.bar', tag_1='value_1').increment()
        recorder.counter('foo.bar', tag_1='value_1').increment()

        recorder.counter('baz.qux').increment()

        assert recorder.unpublished_metrics_count == 3

        metrics = recorder.get_all_metrics()
        assert len(metrics) == 3

        for metric in metrics:
            if metric.name == 'me.foo.bar':
                if metric.value == 3:
                    assert not metric.tags
                else:
                    assert metric.value == 2
                    assert metric.tags['tag_1'] == 'value_1'
            else:
                assert metric.name == 'me.baz.qux'
                assert not metric.tags
                assert metric.value == 1

    def test_gauge(self):
        recorder = self._recorder('you')

        recorder.gauge('foo.bar')
        recorder.gauge('foo.bar').set(3)
        recorder.gauge('baz.qux').set(2)
        recorder.gauge('baz.qux', initial_value=1, tag_2='value_2')

        assert recorder.unpublished_metrics_count == 4

        metrics = recorder.get_all_metrics()
        assert len(metrics) == 4

        possible_foo = {0, 3}

        for metric in metrics:
            if metric.name == 'you.foo.bar':
                assert not metric.tags
                assert metric.value in possible_foo
                possible_foo -= {metric.value}
            elif metric.name == 'you.baz.qux' and not metric.tags:
                assert metric.value == 2
            elif metric.name == 'you.baz.qux':
                assert metric.tags['tag_2'] == 'value_2'
                assert metric.value == 1
            else:
                raise AssertionError(metric.name)

    def test_histogram(self):
        recorder = self._recorder(None, meta=True)

        recorder.histogram('foo.bar').set(4)
        recorder.histogram('foo.bar')
        recorder.histogram('baz.qux').set(17)
        recorder.histogram('baz.qux', initial_value=5, tag_3='value_3')

        assert recorder.unpublished_metrics_count == 4

        metrics = recorder.get_all_metrics()
        assert len(metrics) == 5

        possible_foo = {0, 4}

        for metric in metrics:
            if metric.name == 'foo.bar':
                assert not metric.tags
                assert metric.value in possible_foo
                possible_foo -= {metric.value}
            elif metric.name == 'baz.qux' and not metric.tags:
                assert metric.value == 17
            elif metric.name == 'baz.qux':
                assert metric.tags['tag_3'] == 'value_3'
                assert metric.value == 5
            elif metric.name == 'pymetrics.meta.recorder.get_all_metrics':
                assert metric.value is not None
                assert metric.value > 0
                assert cast(Timer, metric).resolution == TimerResolution.MICROSECONDS
            else:
                raise AssertionError(metric.name)

        assert metrics[0].name == 'pymetrics.meta.recorder.get_all_metrics'

    def test_timer(self):
        recorder = self._recorder('us')

        recorder.timer('foo.bar')
        recorder.timer('foo.bar').set(1)
        recorder.timer('foo.bar', resolution=TimerResolution.MICROSECONDS).set(4)

        recorder.timer('baz.qux')
        recorder.timer('baz.qux', force_new=True).set(2)

        recorder.timer('lorem')
        recorder.timer('lorem', tag_4='value_4')
        recorder.timer('lorem', tag_4='value_4').set(3)

        assert recorder.unpublished_metrics_count == 6

        metrics = recorder.get_all_metrics()
        assert len(metrics) == 4

        possible_foo = {1, 4}

        for metric in metrics:
            if metric.name == 'us.foo.bar':
                assert not metric.tags
                assert metric.value in possible_foo
                possible_foo -= {metric.value}
                if metric.value == 4:
                    assert cast(Timer, metric).resolution == TimerResolution.MICROSECONDS
                else:
                    assert cast(Timer, metric).resolution == TimerResolution.MILLISECONDS
            elif metric.name == 'us.baz.qux':
                assert metric.value == 2
                assert not metric.tags
            elif metric.name == 'us.lorem':
                assert metric.tags['tag_4'] == 'value_4'
                assert metric.value == 3
            else:
                raise AssertionError(metric.name)

        assert len(recorder.timers) == 4
        assert len(recorder.timers['us.foo.bar']) == 2
        assert len(recorder.timers['us.baz.qux']) == 2
        assert len(recorder.timers['us.lorem']) == 1
        assert len(recorder.timers[next(k for k in recorder.timers.keys() if k.startswith('us.lorem#'))]) == 1

        assert recorder.get_all_metrics() == recorder.get_all_metrics()

        recorder.clear(only_published=True)
        assert recorder.unpublished_metrics_count == 2
        assert recorder.get_all_metrics() == []
        assert len(recorder.timers) == 2
        assert len(recorder.timers['us.baz.qux']) == 1
        assert len(recorder.timers['us.lorem']) == 1

        recorder.clear()
        assert recorder.unpublished_metrics_count == 0
        assert recorder.get_all_metrics() == []
        assert len(recorder.timers) == 0

    @mock.patch('pymetrics.recorders.default.publish_metrics')
    def test_publish_no_config(self, mock_publish_metrics):
        recorder = DefaultMetricsRecorder('oops')
        recorder.counter('foo.bar').increment()
        recorder.timer('baz.qux').set(15)

        recorder.publish_all()

        assert recorder.get_all_metrics() == []

        assert mock_publish_metrics.call_count == 0

    @mock.patch('pymetrics.recorders.default.publish_metrics')
    def test_publish_with_config(self, mock_publish_metrics):
        recorder = self._recorder('oops')
        recorder.counter('foo.bar').increment()
        recorder.timer('baz.qux').set(15)

        recorder.publish_all()

        assert recorder.get_all_metrics() == []

        assert mock_publish_metrics.call_count == 1
        args, _ = mock_publish_metrics.call_args

        assert len(args[0]) == 2
        assert args[0][0].name == 'oops.foo.bar'
        assert args[0][0].value == 1
        assert args[0][1].name == 'oops.baz.qux'
        assert args[0][1].value == 15

        assert recorder._configuration is not None
        assert args[1] == recorder._configuration

    def test_publish_if_full_or_old(self):
        recorder = self._recorder('no')

        with mock.patch.object(recorder, 'publish_all') as mock_publish, \
                freezegun.freeze_time() as frozen_time:
            def se():
                recorder._last_publish_timestamp = time.time()

            mock_publish.side_effect = se

            recorder.unpublished_metrics_count = 1
            recorder.publish_if_full_or_old()
            mock_publish.assert_called_once_with()
            mock_publish.reset_mock()

            recorder.publish_if_full_or_old()
            recorder.publish_if_full_or_old()
            recorder.publish_if_full_or_old()
            recorder.publish_if_full_or_old()
            assert mock_publish.call_count == 0

            recorder.unpublished_metrics_count = 18
            recorder.publish_if_full_or_old()
            assert mock_publish.call_count == 0

            recorder.unpublished_metrics_count = 19
            recorder.publish_if_full_or_old()
            mock_publish.assert_called_once_with()
            mock_publish.reset_mock()

            recorder.unpublished_metrics_count = 1
            frozen_time.tick(9)
            recorder.publish_if_full_or_old()
            assert mock_publish.call_count == 0

            frozen_time.tick(1)
            recorder.publish_if_full_or_old()
            mock_publish.assert_called_once_with()
            mock_publish.reset_mock()

            recorder.publish_if_full_or_old()
            recorder.publish_if_full_or_old()
            assert mock_publish.call_count == 0

            frozen_time.tick(13)
            recorder.publish_if_full_or_old(max_age=14)
            assert mock_publish.call_count == 0

            frozen_time.tick(1)
            recorder.publish_if_full_or_old()
            mock_publish.assert_called_once_with()
            mock_publish.reset_mock()

    def test_throttled_publish_all(self):
        recorder = self._recorder('no')

        with mock.patch.object(recorder, 'publish_all') as mock_publish, \
                freezegun.freeze_time() as frozen_time:
            def se():
                recorder._last_publish_timestamp = time.time()

            mock_publish.side_effect = se

            recorder.throttled_publish_all()
            mock_publish.assert_called_once_with()
            mock_publish.reset_mock()

            recorder.throttled_publish_all()
            recorder.throttled_publish_all()
            recorder.throttled_publish_all()
            recorder.throttled_publish_all()
            assert mock_publish.call_count == 0

            frozen_time.tick(9)
            recorder.throttled_publish_all()
            assert mock_publish.call_count == 0

            frozen_time.tick(1)
            recorder.throttled_publish_all()
            mock_publish.assert_called_once_with()
            mock_publish.reset_mock()

            recorder.throttled_publish_all()
            recorder.throttled_publish_all()
            assert mock_publish.call_count == 0

            frozen_time.tick(13)
            recorder.throttled_publish_all(14)
            assert mock_publish.call_count == 0

            frozen_time.tick(1)
            recorder.throttled_publish_all()
            mock_publish.assert_called_once_with()
            mock_publish.reset_mock()
