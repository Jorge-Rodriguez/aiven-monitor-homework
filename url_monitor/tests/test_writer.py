import json
from datetime import datetime
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from psycopg2.extras import DictCursor

from url_monitor.writer import Writer


class KafkaError(BaseException):
    def __init__(self, reason):
        self.reason = reason


mock_config = {
    "kafka": {"connection": {}, "topics": ["mock_topic"]},
    "postgres": {"connection": {}, "batch_size": 1},
}


@pytest.fixture
def message_mock():
    message_mock = MagicMock()
    message_mock.value.return_value = json.dumps(
        {
            "url": "https://mock.site.com",
            "check_time": datetime.now().isoformat(),
            "status": 200,
            "latency": 3,
        }
    )
    message_mock.error.return_value = None
    return message_mock


@pytest.fixture
def message_with_regex_mock():
    message_mock = MagicMock()
    message_mock.value.return_value = json.dumps(
        {
            "url": "https://mock.site.com",
            "check_time": datetime.now().isoformat(),
            "status": 200,
            "latency": 3,
            "regex_match": True,
        }
    )
    message_mock.error.return_value = None
    return message_mock


@patch("url_monitor.writer.Consumer", name="MyConsumer")
@patch("url_monitor.writer.connect")
@patch("url_monitor.writer.Writer.RUNNING", new_callable=PropertyMock)
def test_writer_main_loop(
    loop_check, db_mock, consumer_mock, message_mock, message_with_regex_mock
):
    loop_check.side_effect = [True, True, False]  # Run the main loop only twice
    connection_mock = db_mock.return_value
    consumer_object_mock = consumer_mock.return_value
    consumer_object_mock.poll.side_effect = [message_mock, message_with_regex_mock]
    cursor_mock = MagicMock()
    connection_mock.cursor.return_value.__enter__.return_value = cursor_mock

    Writer(mock_config).run()

    consumer_object_mock.subscribe.assert_called_once()
    assert consumer_object_mock.commit.call_count == 2
    assert consumer_object_mock.poll.call_count == 2

    connection_mock.cursor.assert_called_with(cursor_factory=DictCursor)

    # One call per message
    assert cursor_mock.fetchone.call_count == 2
    # 3 calls on init, 2 calls in message without regex_match, 3 calls in message with regex_match
    assert cursor_mock.execute.call_count == 8

    consumer_object_mock.close.assert_called_once()
    connection_mock.close.assert_called_once()
