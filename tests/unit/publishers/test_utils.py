from __future__ import (
    absolute_import,
    unicode_literals,
)

from typing import cast

import mock

from pymetrics.configuration import Configuration
from pymetrics.instruments import (
    Counter,
    Timer,
)
from pymetrics.publishers.base import MetricsPublisher
from pymetrics.publishers.utils import publish_metrics


def test_publish_metrics():
    publisher1 = mock.MagicMock()
    publisher2 = mock.MagicMock()

    counter1 = Counter('')
    counter2 = Counter('')
    timer1 = Timer('')
    timer2 = Timer('')

    config = Configuration(2, [cast(MetricsPublisher, publisher1), cast(MetricsPublisher, publisher2)])
    publish_metrics([counter1, timer1, counter2], config)

    publisher1.publish.assert_called_once_with([counter1, timer1, counter2], None, False)
    publisher2.publish.assert_called_once_with([counter1, timer1, counter2], None, False)

    publisher1.reset_mock()
    publisher2.reset_mock()

    config = Configuration(2, [cast(MetricsPublisher, publisher2)], 't_py_log', True)
    publish_metrics([timer2, timer1, counter1], config)

    assert publisher1.publish.call_count == 0
    publisher2.publish.assert_called_once_with([timer2, timer1, counter1], 't_py_log', True)
