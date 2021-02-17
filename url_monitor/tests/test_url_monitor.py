import json
from unittest.mock import mock_open, patch

import pytest
import yaml

from url_monitor import application

json_config = json.dumps({"mock": "json"})
yaml_config = yaml.dump({"mock": "yaml"})
bad_config = "THIS IS NOT: {VALID JSON, - OR YAML}"


@patch("url_monitor.application.open", new_callable=mock_open, read_data=json_config)
def test_parse_json_configuration(mock):
    config = application.parse_configuration("mock_config")
    mock.assert_called_once_with("mock_config")
    assert config == json.loads(json_config)


@patch("url_monitor.application.open", new_callable=mock_open, read_data=yaml_config)
def test_parse_yaml_configuration(mock):
    handle = mock.return_value
    handle.seek.side_effect = mock.side_effect
    mock.return_value = handle

    config = application.parse_configuration("mock_config")
    mock.assert_called_once_with("mock_config")
    assert config == yaml.safe_load(yaml_config)


@patch("url_monitor.application.open", new_callable=mock_open, read_data=bad_config)
def test_parse_bad_configuration(mock):
    handle = mock.return_value
    handle.seek.side_effect = mock.side_effect
    mock.return_value = handle

    with pytest.raises(RuntimeError):
        assert application.parse_configuration("mock_config")
    mock.assert_called_once_with("mock_config")
