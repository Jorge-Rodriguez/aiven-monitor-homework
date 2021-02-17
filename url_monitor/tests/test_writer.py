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
    "kafka": {"connection": {}, "topics": ["mock_topic"], "prefetch_count": 1},
    "postgres": {},
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
    return [message_mock]


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
    return [message_mock]


@patch("url_monitor.writer.Consumer", name="MyConsumer")
@patch("url_monitor.writer.connect")
@patch("url_monitor.writer.Writer.RUNNING", new_callable=PropertyMock)
def test_writer_main_loop(
    loop_check, db_mock, consumer_mock, message_mock, message_with_regex_mock
):
    loop_check.side_effect = [True, False]  # Run the main loop only once
    connection_mock = db_mock.return_value
    consumer_object_mock = consumer_mock.return_value
    consumer_object_mock.consume.return_value = message_mock + message_with_regex_mock
    cursor_mock = MagicMock()
    connection_mock.cursor.return_value.__enter__.return_value = cursor_mock

    Writer(mock_config).run()

    consumer_object_mock.subscribe.assert_called_once()
    consumer_object_mock.consume.assert_called_once()
    consumer_object_mock.commit.assert_called_once()

    connection_mock.cursor.assert_called_with(cursor_factory=DictCursor)

    # One call per message
    assert cursor_mock.fetch_one.call_count == 2
    # 3 calls on init, 2 calls in message without regex_match, 3 calls in message with regex_match
    assert cursor_mock.execute.call_count == 8

    consumer_object_mock.close.assert_called_once()
    connection_mock.close.assert_called_once()


@patch("url_monitor.writer.Consumer")
@patch("url_monitor.writer.connect")
@patch("url_monitor.writer.Writer.RUNNING", new_callable=PropertyMock)
def test_writer_consume_exception(loop_check, db_mock, consumer_mock):
    loop_check.side_effect = [True, False]  # Run the main loop only once
    consumer_object_mock = consumer_mock.return_value
    consumer_object_mock.consume.side_effect = KafkaError("Mock Kafka Error")

    # Monkey patch writer's KafkaError to properly handle the mock's side effect
    import url_monitor.writer

    url_monitor.writer.KafkaError = KafkaError

    Writer(mock_config).run()

    consumer_object_mock.subscribe.assert_called_once()
    consumer_object_mock.consume.assert_called_once()
    consumer_object_mock.commit.assert_not_called()
    db_mock.return_value.assert_not_called()
