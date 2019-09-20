from __future__ import (
    absolute_import,
    unicode_literals,
)

import copy
import functools
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    Union,
    cast,
)

import attr
from conformity import (
    fields,
    validator,
)
from conformity.error import ValidationError
import six

from pymetrics.publishers.base import MetricsPublisher


__all__ = (
    'Configuration',
    'CONFIGURATION_SCHEMA',
    'create_configuration',
)


_StringField = fields.UnicodeString  # type: Union[Type[fields.UnicodeString], Type[fields.Any]]
if six.PY2:
    # noinspection PyTypeChecker
    _StringField = cast(Type[Any], functools.partial(fields.Any, fields.UnicodeString(), fields.ByteString()))


_enable_meta_metrics = fields.Boolean(
    description='If true, meta-metrics will be recorded documenting the performance of PyMetrics itself.',
)

_error_logger_name = _StringField(
    description='By default, errors encountered when publishing metrics are suppressed and lost. If this value is'
                'truthy, a Logger is created with this name and used to log publication errors.',
)

CONFIGURATION_SCHEMA = fields.Polymorph(
    switch_field='version',
    contents_map={
        1: fields.Dictionary(
            {
                'version': fields.Constant(1),
                'enable_meta_metrics': _enable_meta_metrics,
                'error_logger_name': _error_logger_name,
                'publishers': fields.Sequence(
                    fields.Dictionary(
                        {'class': _StringField(description='The import path of the publisher.')},
                        allow_extra_keys=True,
                        description='Import path and arguments for a publisher.',
                    ),
                    min_length=1,
                    description='The configuration for all publishers.',
                ),
            },
            optional_keys=('enable_meta_metrics', 'error_logger_name'),
        ),
        2: fields.Dictionary(
            {
                'version': fields.Constant(2),
                'enable_meta_metrics': _enable_meta_metrics,
                'error_logger_name': fields.UnicodeString(description=_error_logger_name.description),
                'publishers': fields.Sequence(
                    fields.ClassConfigurationSchema(
                        base_class=MetricsPublisher,
                        description='Import path and arguments for a publisher.',
                    ),
                    min_length=1,
                    description='The configuration for all publishers.',
                ),
            },
            optional_keys=('enable_meta_metrics', 'error_logger_name'),
        ),
    },
    description='The configuration schema changes slightly based on which config version you specify.',
)
""""""  # Empty docstring to make autodoc document this data


@attr.s
class Configuration(object):
    version = attr.ib()  # type: int
    publishers = attr.ib(default=attr.Factory(list))  # type: List[MetricsPublisher]
    error_logger_name = attr.ib(default=None)  # type: Optional[six.text_type]
    enable_meta_metrics = attr.ib(default=False)  # type: bool


@validator.validate_call(
    args=fields.Tuple(copy.deepcopy(CONFIGURATION_SCHEMA)),
    kwargs=None,
    returns=fields.ObjectInstance(Configuration),
)
def create_configuration(config_dict):  # type: (Dict[six.text_type, Any]) -> Configuration
    """
    Creates a `Configuration` object using the provided configuration dictionary. Works in similar fashion to logging's
    configuration.

    Expected format of config is a dict:

    .. code-block:: python

        {
            'version': 2,
            'error_logger_name': 'pymetrics',  # name of the error logger to use, or `None` (the default) to suppress
            'enable_meta_metrics': False,  # whether to enable the collection of meta-metrics
            'publishers': [
                {
                    'path': 'path.to.publisher:ClassName',
                    'kwargs': {
                        ...  # constructor arguments for the publisher
                    },
                },
            ],
        }

    If multiple publishers are specified, metrics will be emitted to each publisher in the order it is specified in
    the configuration list.
    """
    configuration = Configuration(
        version=config_dict['version'],
        enable_meta_metrics=config_dict.get('enable_meta_metrics', False),
        error_logger_name=config_dict.get('error_logger_name'),
    )

    for publisher in config_dict['publishers']:
        if configuration.version == 1:
            try:
                publisher_class = fields.TypePath.resolve_python_path(publisher['class'])
            except (ValueError, ImportError, AttributeError) as e:
                raise ValidationError('Could not import publisher {path}: {error}'.format(
                    path=publisher['class'],
                    error=e.args[0],
                ))
            params = copy.deepcopy(publisher)
            del params['class']
            configuration.publishers.append(publisher_class(**params))

        else:
            configuration.publishers.append(
                publisher['object'](**publisher.get('kwargs', {})),
            )

    return configuration
