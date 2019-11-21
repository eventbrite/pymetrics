from __future__ import (
    absolute_import,
    unicode_literals,
)

from conformity.error import ValidationError
import pytest

from pymetrics.configuration import create_configuration


class TestConfiguration(object):
    def test_create_config_invalid_version(self):  # type: () -> None
        with pytest.raises(ValidationError) as error_context:
            create_configuration({'version': 92, 'futuristic': 'Not a real config'})

        assert "0: Invalid switch value '92'" in error_context.value.args[0]

    def test_create_config_v1_has_been_retired(self):  # type: () -> None
        with pytest.raises(ValidationError) as error_context:
            create_configuration({
                'version': 1,
                'error_logger_name': 'py_metrics_errors',
                'enable_meta_metrics': True,
                'publishers': [
                    {'class': 'pymetrics.publishers.statsd.StatsdPublisher', 'host': 'localhost', 'port': 9876},
                    {'class': 'pymetrics.publishers.logging.LogPublisher', 'log_name': 'py_metrics'},
                    {'class': 'pymetrics.publishers.null.NullPublisher'},
                ],
            })

        assert "0: Invalid switch value '1'" in error_context.value.args[0]

    def test_create_config_v2_extra_key(self):  # type: () -> None
        with pytest.raises(ValidationError) as error_context:
            create_configuration({
                'version': 2,
                'unknown_key': 'Unexpected key',
                'publishers': [
                    {'path': 'pymetrics.publishers.logging.LogPublisher', 'kwargs': {'log_name': 'py_metrics'}},
                ],
            })

        assert '0: Extra keys present: unknown_key' in error_context.value.args[0]

    def test_create_config_v2_missing_publishers(self):  # type: () -> None
        with pytest.raises(ValidationError) as error_context:
            create_configuration({
                'version': 2,
            })

        assert '0.publishers: Missing key: publishers' in error_context.value.args[0]

    def test_create_config_v12_invalid_publisher(self):  # type: () -> None
        with pytest.raises(ValidationError) as error_context:
            create_configuration({
                'version': 2,
                'publishers': [{}],
            })

        assert '0.publishers.0.path: Missing key (and no default specified): path' in error_context.value.args[0]

    def test_create_config_v2_non_existent_publisher(self):  # type: () -> None
        with pytest.raises(ValidationError) as error_context:
            create_configuration({
                'version': 2,
                'publishers': [
                    {'path': 'pymetrics.publishers.NotARealPublisher'},
                ],
            })

        assert '0.publishers.0.path: ' in error_context.value.args[0]
        assert 'module' in error_context.value.args[0]
        assert "has no attribute 'NotARealPublisher'" in error_context.value.args[0]

    def test_create_config_v2_success(self):  # type: () -> None
        configuration = create_configuration({
            'version': 2,
            'publishers': [
                {'path': 'pymetrics.publishers.logging.LogPublisher', 'kwargs': {'log_name': 'py_metrics'}},
            ],
        })

        assert configuration.version == 2
        assert configuration.error_logger_name is None
        assert configuration.enable_meta_metrics is False
        assert len(configuration.publishers) == 1
        assert configuration.publishers[0].__class__.__name__ == 'LogPublisher'

    def test_create_config_v2_success_optional_settings(self):  # type: () -> None
        configuration = create_configuration({
            'version': 2,
            'error_logger_name': 'py_metrics_errors',
            'enable_meta_metrics': True,
            'publishers': [
                {'path': 'pymetrics.publishers.statsd.StatsdPublisher', 'kwargs': {'host': 'localhost', 'port': 9876}},
                {'path': 'pymetrics.publishers.logging.LogPublisher', 'kwargs': {'log_name': 'py_metrics'}},
                {'path': 'pymetrics.publishers.null.NullPublisher'},
            ],
        })

        assert configuration.version == 2
        assert configuration.error_logger_name == 'py_metrics_errors'
        assert configuration.enable_meta_metrics is True
        assert len(configuration.publishers) == 3
        assert configuration.publishers[0].__class__.__name__ == 'StatsdPublisher'
        assert configuration.publishers[1].__class__.__name__ == 'LogPublisher'
        assert configuration.publishers[2].__class__.__name__ == 'NullPublisher'
