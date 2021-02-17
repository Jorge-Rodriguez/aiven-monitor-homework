from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from confluent_kafka import KafkaException
from requests.exceptions import RequestException, Timeout

from url_monitor.monitor import Monitor

mock_config = {
    "kafka": {"connection": {}, "topic": "mock_topic"},
    "targets": [
        {"url": "https://mock.site.com", "frequency": 1, "regex": ".*mock site.*"}
    ],
}


@pytest.fixture
def response_mock():
    response_mock = MagicMock()
    type(response_mock).url = PropertyMock(
        return_value=mock_config["targets"][0]["url"]
    )
    type(response_mock).elapsed = PropertyMock(return_value=3)
    type(response_mock).status_code = PropertyMock(return_value=200)
    type(response_mock).text = PropertyMock(
        return_value="This is a mock site for testing."
    )
    return response_mock


@patch("url_monitor.monitor.Producer")
@patch("url_monitor.monitor.get")
@patch("url_monitor.monitor.Monitor.RUNNING", new_callable=PropertyMock)
def test_monitor_main_loop(loop_check, get_mock, producer_mock, response_mock):
    loop_check.side_effect = [True, False]  # Run the main loop only once
    get_mock.return_value = response_mock
    producer_object_mock = producer_mock.return_value

    Monitor(mock_config).run()

    producer_object_mock.produce.assert_called_once()
    producer_object_mock.poll.assert_called_once()


@patch("url_monitor.monitor.Monitor.produce")
@patch("url_monitor.monitor.get")
@patch("url_monitor.monitor.Monitor.RUNNING", new_callable=PropertyMock)
def test_monitor_get_timeout(loop_check, get_mock, producer_mock):
    loop_check.side_effect = [True, False]  # Run the main loop only once
    get_mock.side_effect = Timeout("Mock timeout")

    Monitor(mock_config).run()

    producer_mock.assert_not_called()


@patch("url_monitor.monitor.Monitor.produce")
@patch("url_monitor.monitor.get")
@patch("url_monitor.monitor.Monitor.RUNNING", new_callable=PropertyMock)
def test_monitor_get_exception(loop_check, get_mock, producer_mock):
    loop_check.side_effect = [True, False]  # Run the main loop only once
    get_mock.side_effect = RequestException("Mock Exception")

    Monitor(mock_config).run()

    producer_mock.assert_not_called()


@patch("url_monitor.monitor.Producer")
@patch("url_monitor.monitor.get")
@patch("url_monitor.monitor.Monitor.RUNNING", new_callable=PropertyMock)
def test_monitor_producer_exception(loop_check, get_mock, producer_mock, response_mock):
    loop_check.side_effect = [True, False]  # Run the main loop only once
    get_mock.return_value = response_mock
    producer_object_mock = producer_mock.return_value
    producer_object_mock.produce.side_effect = KafkaException("mock Kafka error")

    Monitor(mock_config).run()

    producer_object_mock.produce.assert_called_once()
    producer_object_mock.poll.assert_not_called()
