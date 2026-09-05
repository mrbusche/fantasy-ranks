import json
import os
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

from scripts.espn_rosters import (
    check_if_update_needed_for_league,
    fetch_and_export_data,
    file_needs_update,
)


def test_file_needs_update_non_existent(tmp_path):
    missing = str(tmp_path / 'missing.json')
    assert file_needs_update(missing) is True


def test_file_needs_update_recent(tmp_path):
    recent = tmp_path / 'recent.json'
    recent.write_text('{}', encoding='utf-8')
    assert file_needs_update(str(recent), max_age_hours=1) is False


def test_file_needs_update_old(tmp_path):
    old = tmp_path / 'old.json'
    old.write_text('{}', encoding='utf-8')
    past_time = datetime.now(UTC).timestamp() - 7200
    os.utime(str(old), (past_time, past_time))
    assert file_needs_update(str(old), max_age_hours=1) is True


def test_check_if_update_needed_for_league_needed():
    with patch('scripts.espn_rosters.file_needs_update', return_value=True):
        assert check_if_update_needed_for_league(12345) is True


def test_check_if_update_needed_for_league_not_needed(tmp_path):
    fake_file = tmp_path / 'espn_12345_owned_players.json'
    fake_file.write_text('{}', encoding='utf-8')
    with (
        patch('scripts.espn_rosters.ROSTERS_DIR', str(tmp_path)),
        patch('scripts.espn_rosters.file_needs_update', return_value=False),
    ):
        assert check_if_update_needed_for_league(12345) is False


def test_fetch_and_export_data_success(tmp_path):
    player1 = SimpleNamespace(
        name='Patrick Mahomes',
        position='QB',
        proTeam='KC',
        injured=False,
        total_points=250.5,
    )
    player2 = SimpleNamespace(
        name='Travis Kelce',
        position='TE',
        proTeam='KC',
        injured=True,
        total_points=180.2,
    )
    team1 = SimpleNamespace(
        team_name='Chiefs Kingdom',
        roster=[player1, player2],
    )
    mock_league = SimpleNamespace(teams=[team1])

    with (
        patch('scripts.espn_rosters.League', return_value=mock_league),
        patch('scripts.espn_rosters.ROSTERS_DIR', str(tmp_path)),
    ):
        fetch_and_export_data(12345, 'half')

    exported_file = tmp_path / 'espn_12345_owned_players.json'
    assert exported_file.exists()

    data = json.loads(exported_file.read_text(encoding='utf-8'))
    assert 'Chiefs Kingdom' in data
    assert len(data['Chiefs Kingdom']) == 2
    assert data['Chiefs Kingdom'][0]['name'] == 'Patrick Mahomes'
    assert data['Chiefs Kingdom'][0]['totalPoints'] == 250.5
    assert data['Chiefs Kingdom'][1]['injured'] is True


def test_fetch_and_export_data_connection_failure():
    with patch('scripts.espn_rosters.League', side_effect=RuntimeError('Auth failed')):
        # Should catch error and not raise
        fetch_and_export_data(12345, 'half')


def test_fetch_and_export_data_handles_league_value_error():
    with patch('scripts.espn_rosters.League', side_effect=ValueError('invalid league')):
        fetch_and_export_data(12345, 'half')
