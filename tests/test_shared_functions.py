import json
from unittest.mock import patch

import pytest

from fantasy_ranks.shared_functions import (
    get_all_owned_players,
    get_required_column,
    load_league_config,
    load_owned_players,
    names_match,
    normalize_name,
    validate_league,
)


def test_get_required_column_success():
    row = {'Player Name': 'CeeDee Lamb', 'Rank': '1'}
    assert get_required_column(row, 'Player Name', 'PLAYER_NAME_COLUMN', 'test.csv') == 'CeeDee Lamb'


def test_get_required_column_missing():
    row = {'Name': 'CeeDee Lamb'}
    with pytest.raises(ValueError, match="Column 'Player Name' not found in test.csv"):
        get_required_column(row, 'Player Name', 'PLAYER_NAME_COLUMN', 'test.csv')


def test_normalize_name():
    assert normalize_name('') == ''
    assert normalize_name('Marvin Harrison Jr.') == 'marvin harrison'
    assert normalize_name('Kenneth Walker III') == 'kenneth walker'
    assert normalize_name('Tetairoa McMillan') == 'tet mcmillan'
    assert normalize_name('Kenny Gainwell') == 'kenneth gainwell'
    assert normalize_name("De'Von Achane") == 'devon achane'


def test_names_match():
    assert names_match('Marvin Harrison Jr.', 'Marvin Harrison') is True
    assert names_match('Kenneth Gainwell', 'Kenny Gainwell') is True
    assert names_match('Patrick Mahomes', 'Josh Allen') is False


def test_load_owned_players_success(tmp_path):
    owned_file = tmp_path / 'owned.json'
    owned_file.write_text('{"Team A": [{"name": "Player 1"}]}', encoding='utf-8')
    assert load_owned_players(owned_file) == {'Team A': [{'name': 'Player 1'}]}


def test_load_owned_players_errors(tmp_path):
    assert load_owned_players(tmp_path / 'missing.json') is None
    bad_json = tmp_path / 'bad.json'
    bad_json.write_text('{ bad }', encoding='utf-8')
    assert load_owned_players(bad_json) is None


def test_get_all_owned_players():
    data = {
        'Team 1': [{'name': 'Marvin Harrison Jr.'}],
        'Team 2': [{'name': 'Josh Allen'}],
    }
    owned = get_all_owned_players(data)
    assert 'Marvin Harrison Jr.' in owned
    assert 'marvin harrison' in owned
    assert 'Josh Allen' in owned


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

    with patch('fantasy_ranks.shared_functions.Path') as mock_path:
        mock_path.return_value.parent.parent.parent.__truediv__.return_value = fake_config
        result = load_league_config()
        assert result == {'leagues': []}


@pytest.mark.parametrize(
    'league',
    [
        {'platform': 'espn', 'league_id': '12345', 'scoring_type': 'half', 'team_name': 'My Team'},
        {'platform': 'sleeper', 'league_id': 12345, 'scoring_type': 'full', 'team_name': 'My Team'},
        {'platform': 'yahoo', 'league_id': '67890', 'scoring_type': 'half', 'team_name': 'My Team'},
    ],
)
def test_validate_league_valid(league):
    assert validate_league(league) == []


def test_validate_league_invalid_platform():
    league = {'platform': 'nfl', 'league_id': '12345', 'scoring_type': 'half', 'team_name': 'My Team'}
    errors = validate_league(league)
    assert len(errors) == 1
    assert 'platform' in errors[0]


def test_validate_league_missing_platform():
    league = {'league_id': '12345', 'scoring_type': 'half', 'team_name': 'My Team'}
    errors = validate_league(league)
    assert any('platform' in error for error in errors)


def test_validate_league_non_numeric_league_id():
    league = {'platform': 'espn', 'league_id': 'abc123', 'scoring_type': 'half', 'team_name': 'My Team'}
    errors = validate_league(league)
    assert any('league_id' in error for error in errors)


def test_validate_league_invalid_scoring_type():
    league = {'platform': 'espn', 'league_id': '12345', 'scoring_type': 'ppr', 'team_name': 'My Team'}
    errors = validate_league(league)
    assert any('scoring_type' in error for error in errors)


def test_validate_league_missing_team_name():
    league = {'platform': 'espn', 'league_id': '12345', 'scoring_type': 'half'}
    errors = validate_league(league)
    assert any('team_name' in error for error in errors)


def test_validate_league_blank_team_name():
    league = {'platform': 'espn', 'league_id': '12345', 'scoring_type': 'half', 'team_name': '   '}
    errors = validate_league(league)
    assert any('team_name' in error for error in errors)


def test_validate_league_multiple_errors():
    league = {'platform': 'nfl', 'league_id': 'abc', 'scoring_type': 'ppr', 'team_name': ''}
    errors = validate_league(league)
    assert len(errors) == 4


def test_load_league_config_skips_invalid_leagues(tmp_path):
    config_data = {
        'leagues': [
            {'platform': 'espn', 'league_id': '12345', 'scoring_type': 'half', 'team_name': 'Valid Team'},
            {'platform': 'yahoo', 'league_id': '999', 'scoring_type': 'full', 'team_name': 'Yahoo Team'},
            {'platform': 'sleeper', 'league_id': 'abc', 'scoring_type': 'full', 'team_name': 'Bad League Id'},
            {'platform': 'espn', 'league_id': '111', 'scoring_type': 'ppr', 'team_name': 'Bad Scoring Type'},
            {'platform': 'espn', 'league_id': '222', 'scoring_type': 'half'},
        ]
    }
    config_file = tmp_path / 'config.json'
    config_file.write_text(json.dumps(config_data), encoding='utf-8')

    result = load_league_config(config_file)
    assert len(result['leagues']) == 2
    assert [league['team_name'] for league in result['leagues']] == ['Valid Team', 'Yahoo Team']
