# type: ignore
from __future__ import (
    absolute_import,
    unicode_literals,
)

from invoke_release.tasks import *  # noqa: F403


configure_release_parameters(  # noqa: F405
    module_name='pymetrics',
    display_name='PyMetrics',
    use_pull_request=True,
)
