from __future__ import (
    absolute_import,
    unicode_literals,
)

import copy
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import attr
from conformity import (
    fields,
    validator,
)
import six

from pymetrics.publishers.base import MetricsPublisher


__all__ = (
    'Configuration',
    'CONFIGURATION_SCHEMA',
    'create_configuration',
)


CONFIGURATION_SCHEMA = fields.Polymorph(
    switch_field='version',
    contents_map={
        2: fields.Dictionary(
            {
                'version': fields.Constant(2),
                'enable_meta_metrics': fields.Boolean(
                    description='If true, meta-metrics will be recorded documenting the performance of '
                                'PyMetrics itself.',
                ),
                'error_logger_name': fields.UnicodeString(
                    description='By default, errors encountered when publishing metrics are suppressed and lost. If '
                                'this value is truthy, a Logger is created with this name and used to log publication '
                                'errors.',
                ),
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
        configuration.publishers.append(publisher['object'](**publisher.get('kwargs', {})))

    return configuration
