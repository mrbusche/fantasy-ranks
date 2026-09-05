import json
from unittest.mock import patch

from scripts.shared_functions import load_league_config


def test_load_league_config_success(tmp_path):
    config_data = {
        'leagues': [{'league_id': 12345, 'platform': 'espn', 'scoring_type': 'half', 'team_name': 'My Team'}]
    }
    config_file = tmp_path / 'config.json'
    config_file.write_text(json.dumps(config_data), encoding='utf-8')

    result = load_league_config(config_file)
    assert result == config_data


def test_load_league_config_file_not_found(tmp_path):
    non_existent = tmp_path / 'non_existent.json'
    result = load_league_config(non_existent)
    assert result is None


def test_load_league_config_invalid_json(tmp_path):
    invalid_file = tmp_path / 'invalid.json'
    invalid_file.write_text('{ invalid json }', encoding='utf-8')
    result = load_league_config(invalid_file)
    assert result is None


def test_load_league_config_default_path(tmp_path):
    fake_config = tmp_path / 'config.json'
    fake_config.write_text('{"leagues": []}', encoding='utf-8')

    with patch('scripts.shared_functions.Path') as mock_path:
        mock_path.return_value.parent.parent.__truediv__.return_value = fake_config
        result = load_league_config()
        assert result == {'leagues': []}
