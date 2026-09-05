import json
import os
import time
from unittest.mock import MagicMock, patch

import requests

from scripts.sleeper_rosters import (
    extract_player_data,
    get_all_players_db,
    get_league_rosters,
    get_league_users,
    main,
    needs_refresh,
)


def test_needs_refresh_non_existent(tmp_path):
    missing = str(tmp_path / 'missing.json')
    assert needs_refresh(missing, 3600) is True


def test_needs_refresh_recent(tmp_path):
    recent = tmp_path / 'recent.json'
    recent.write_text('{}', encoding='utf-8')
    assert needs_refresh(str(recent), 3600) is False


def test_needs_refresh_old(tmp_path):
    old = tmp_path / 'old.json'
    old.write_text('{}', encoding='utf-8')
    past_time = time.time() - 7200
    os.utime(str(old), (past_time, past_time))
    assert needs_refresh(str(old), 3600) is True


def test_get_all_players_db_from_cache(tmp_path):
    cache_file = tmp_path / 'sleeper_master_players.json'
    expected_data = {'123': {'first_name': 'Josh', 'last_name': 'Allen'}}
    cache_file.write_text(json.dumps(expected_data), encoding='utf-8')

    with (
        patch('scripts.sleeper_rosters.MASTER_PLAYERS_FILE', str(cache_file)),
        patch('scripts.sleeper_rosters.needs_refresh', return_value=False),
    ):
        result = get_all_players_db()
        assert result == expected_data


def test_get_all_players_db_from_api(tmp_path):
    cache_file = tmp_path / 'sleeper_master_players.json'
    api_data = {'456': {'first_name': 'Lamar', 'last_name': 'Jackson'}}

    mock_resp = MagicMock()
    mock_resp.json.return_value = api_data
    mock_resp.raise_for_status.return_value = None

    with (
        patch('scripts.sleeper_rosters.MASTER_PLAYERS_FILE', str(cache_file)),
        patch('scripts.sleeper_rosters.ROSTERS_DIR', str(tmp_path)),
        patch('scripts.sleeper_rosters.needs_refresh', return_value=True),
        patch('requests.get', return_value=mock_resp),
    ):
        result = get_all_players_db()
        assert result == api_data
        assert cache_file.exists()


def test_get_all_players_db_api_error():
    with (
        patch('scripts.sleeper_rosters.needs_refresh', return_value=True),
        patch('requests.get', side_effect=requests.RequestException('Network error')),
    ):
        result = get_all_players_db()
        assert result == {}


def test_get_league_users():
    mock_users = [
        {'user_id': 'u1', 'display_name': 'User One', 'metadata': {'team_name': 'Team Alpha'}},
        {'user_id': 'u2', 'display_name': 'User Two', 'metadata': {}},
        {'user_id': 'u3', 'display_name': None, 'metadata': {}},
    ]
    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_users
    mock_resp.raise_for_status.return_value = None

    with patch('requests.get', return_value=mock_resp):
        user_map = get_league_users('league_123')

    assert user_map['u1'] == 'Team Alpha'
    assert user_map['u2'] == 'User Two'
    assert user_map['u3'] == 'Unknown Team'


def test_get_league_rosters():
    mock_rosters = [{'roster_id': 1, 'owner_id': 'u1', 'players': ['1', '2']}]
    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_rosters
    mock_resp.raise_for_status.return_value = None

    with patch('requests.get', return_value=mock_resp):
        rosters = get_league_rosters('league_123')

    assert rosters == mock_rosters


def test_extract_player_data_standard():
    db = {
        '100': {
            'first_name': 'Saquon',
            'last_name': 'Barkley',
            'position': 'RB',
            'team': 'PHI',
            'injury_status': 'Questionable',
            'status': 'Active',
            'search_rank': 5,
        }
    }
    result = extract_player_data('100', db)
    assert result == {
        'player_id': '100',
        'name': 'Saquon Barkley',
        'position': 'RB',
        'nfl_team': 'PHI',
        'status': 'Questionable',
        'rank': 5,
    }


def test_extract_player_data_defense_and_defaults():
    db = {
        'DEF_SF': {
            'first_name': 'San Francisco',
            'last_name': '49ers',
            'position': 'DEF',
            'team': None,
            'injury_status': None,
            'status': None,
            'search_rank': None,
        }
    }
    result = extract_player_data('DEF_SF', db)
    assert result == {
        'player_id': 'DEF_SF',
        'name': 'San Francisco 49ers',
        'position': 'D/ST',
        'nfl_team': 'FA',
        'status': 'Inactive',
        'rank': 999999,
    }


def test_main_cached(monkeypatch):
    monkeypatch.setattr('sys.argv', ['sleeper_rosters.py', '--league-id', '999'])
    with (
        patch('scripts.sleeper_rosters.needs_refresh', return_value=False),
        patch('os.path.getmtime', return_value=time.time()),
    ):
        main()


def test_main_full_flow(monkeypatch, tmp_path):
    monkeypatch.setattr('sys.argv', ['sleeper_rosters.py', '--league-id', '999', '--ppr', 'half'])

    player_db = {
        'p1': {'first_name': 'Justin', 'last_name': 'Jefferson', 'position': 'WR', 'team': 'MIN', 'search_rank': 1}
    }
    users = {'u1': 'Vikings Fan'}
    rosters = [{'owner_id': 'u1', 'players': ['p1'], 'starters': ['p1']}]

    with (
        patch('scripts.sleeper_rosters.ROSTERS_DIR', str(tmp_path)),
        patch('scripts.sleeper_rosters.needs_refresh', return_value=True),
        patch('scripts.sleeper_rosters.get_all_players_db', return_value=player_db),
        patch('scripts.sleeper_rosters.get_league_users', return_value=users),
        patch('scripts.sleeper_rosters.get_league_rosters', return_value=rosters),
    ):
        main()

    output_file = tmp_path / 'sleeper_999_owned_players.json'
    assert output_file.exists()
    data = json.loads(output_file.read_text(encoding='utf-8'))
    assert 'Vikings Fan' in data
    assert data['Vikings Fan'][0]['name'] == 'Justin Jefferson'
    assert data['Vikings Fan'][0]['roster_status'] == 'Starter'


def test_main_db_load_failure(monkeypatch):
    monkeypatch.setattr('sys.argv', ['sleeper_rosters.py', '--league-id', '999'])
    with (
        patch('scripts.sleeper_rosters.needs_refresh', return_value=True),
        patch('scripts.sleeper_rosters.get_all_players_db', return_value={}),
    ):
        main()


def test_main_processing_error(monkeypatch):
    monkeypatch.setattr('sys.argv', ['sleeper_rosters.py', '--league-id', '999'])
    with (
        patch('scripts.sleeper_rosters.needs_refresh', return_value=True),
        patch('scripts.sleeper_rosters.get_all_players_db', return_value={'p1': {}}),
        patch('scripts.sleeper_rosters.get_league_users', side_effect=ValueError('bad data')),
    ):
        main()
