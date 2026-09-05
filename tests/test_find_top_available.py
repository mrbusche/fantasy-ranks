import json
from unittest.mock import patch

from scripts.find_top_available import (
    find_available_for_league,
    find_team_players_with_rankings,
    find_top_available_players,
    get_owned_players_by_league_with_teams,
    is_player_owned,
    load_ros_rankings,
)


def test_load_ros_rankings(tmp_path):
    rankings_file = tmp_path / 'rest-of-season.csv'
    rankings_file.write_text(
        'Player,Position,Rank,Team\nJosh Allen,QB,2,BUF\nSaquon Barkley,RB,1,PHI\n',
        encoding='utf-8',
    )

    assert load_ros_rankings(rankings_file) == [
        {'name': 'Josh Allen', 'position': 'QB', 'team': 'BUF', 'rank': 2},
        {'name': 'Saquon Barkley', 'position': 'RB', 'team': 'PHI', 'rank': 1},
    ]


def test_load_ros_rankings_returns_empty_for_invalid_csv(tmp_path):
    rankings_file = tmp_path / 'invalid.csv'
    rankings_file.write_text('Player,Position,Rank\nJosh Allen,QB,2\n', encoding='utf-8')

    assert load_ros_rankings(rankings_file) == []


def test_is_player_owned_handles_normalized_and_defense_names():
    assert is_player_owned({'name': 'Marvin Harrison Jr.', 'position': 'WR'}, {'Marvin Harrison'})
    assert is_player_owned({'name': 'San Francisco 49ers D/ST', 'position': 'D/ST'}, {'San Francisco 49ers'})
    assert not is_player_owned({'name': 'Josh Allen', 'position': 'QB'}, {'Patrick Mahomes'})


def test_find_available_for_league_sorts_and_limits_results():
    rankings = [
        {'name': f'Player {rank:02d}', 'position': 'WR', 'team': 'TST', 'rank': rank} for rank in range(12, 0, -1)
    ]

    available = find_available_for_league(rankings, {'Player 01'})

    assert len(available) == 10
    assert [player['rank'] for player in available] == list(range(2, 12))


def test_find_team_players_with_rankings_includes_unranked_players():
    team_data = {
        'Team A': [
            {'name': 'Marvin Harrison Jr.', 'position': 'WR', 'proTeam': 'ARI'},
            {'name': 'Unknown Player', 'position': 'RB', 'proTeam': 'FA'},
        ]
    }
    rankings = [{'name': 'Marvin Harrison', 'position': 'WR', 'team': 'ARI', 'rank': 10}]

    assert find_team_players_with_rankings('Team A', team_data, rankings) == [
        {'name': 'Marvin Harrison Jr.', 'position': 'WR', 'team': 'ARI', 'rank': 10},
        {'name': 'Unknown Player', 'position': 'RB', 'team': 'FA', 'rank': 999},
    ]
    assert find_team_players_with_rankings('Missing Team', team_data, rankings) == []


def test_get_owned_players_by_league_with_teams(tmp_path):
    rosters_dir = tmp_path / 'rosters'
    rosters_dir.mkdir()
    roster_file = rosters_dir / 'espn_123_owned_players.json'
    roster_file.write_text(json.dumps({'Team A': [{'name': 'Josh Allen'}]}), encoding='utf-8')

    module_file = tmp_path / 'scripts' / 'find_top_available.py'
    module_file.parent.mkdir()
    module_file.write_text('', encoding='utf-8')
    config = {
        'leagues': [
            {
                'platform': 'espn',
                'league_id': '123',
                'scoring_type': 'half',
                'league_name': 'League A',
                'team_name': 'Team A',
            }
        ]
    }

    with patch('scripts.find_top_available.__file__', str(module_file)):
        leagues, full_data = get_owned_players_by_league_with_teams(config)

    assert leagues == {'League A': {'Josh Allen'}}
    assert full_data == {'League A': {'Team A': [{'name': 'Josh Allen'}]}}


def test_get_owned_players_by_league_with_teams_handles_invalid_and_missing_data(tmp_path):
    module_file = tmp_path / 'scripts' / 'find_top_available.py'
    module_file.parent.mkdir()
    module_file.write_text('', encoding='utf-8')
    config = {
        'leagues': [
            {'league_name': 'Missing Scoring', 'platform': 'espn', 'league_id': '1'},
            {'league_name': 'Missing File', 'scoring_type': 'half', 'platform': 'espn', 'league_id': '2'},
            {'league_name': 'Bad File', 'scoring_type': 'half', 'platform': 'espn', 'league_id': '3'},
        ]
    }
    rosters_dir = tmp_path / 'rosters'
    rosters_dir.mkdir()
    (rosters_dir / 'espn_3_owned_players.json').write_text('{}', encoding='utf-8')

    with patch('scripts.find_top_available.__file__', str(module_file)):
        leagues, full_data = get_owned_players_by_league_with_teams(config)

    assert leagues == {}
    assert full_data == {}
    assert get_owned_players_by_league_with_teams(None) == ({}, {})


def test_find_top_available_players_writes_analysis(tmp_path):
    module_file = tmp_path / 'scripts' / 'find_top_available.py'
    module_file.parent.mkdir()
    module_file.write_text('', encoding='utf-8')
    output_dir = tmp_path / 'lineups'
    output_dir.mkdir()
    rankings = [
        {'name': 'Free Player', 'position': 'WR', 'team': 'TST', 'rank': 1},
        {'name': 'Owned Player', 'position': 'RB', 'team': 'TST', 'rank': 2},
    ]
    league_data = {'Team A': [{'name': 'Owned Player', 'position': 'RB', 'proTeam': 'TST'}]}
    config = {'leagues': [{'league_name': 'League A', 'team_name': 'Team A'}]}

    with (
        patch('scripts.find_top_available.__file__', str(module_file)),
        patch('scripts.find_top_available.load_ros_rankings', return_value=rankings),
        patch('scripts.find_top_available.get_owned_players_by_league_with_teams', return_value=({'League A': {'Owned Player'}}, {'League A': league_data})),
    ):
        find_top_available_players(config)

    output = (output_dir / 'ros-analysis.md').read_text(encoding='utf-8')
    assert '## League A Team A' in output
    assert '| 1 | Free Player | WR | TST |' in output
    assert '| 2 | Owned Player | RB | TST |' in output


def test_find_top_available_players_handles_missing_rankings_and_leagues(tmp_path):
    module_file = tmp_path / 'scripts' / 'find_top_available.py'
    module_file.parent.mkdir()
    module_file.write_text('', encoding='utf-8')
    with (
        patch('scripts.find_top_available.__file__', str(module_file)),
        patch('scripts.find_top_available.load_ros_rankings', return_value=[]),
    ):
        assert find_top_available_players({'leagues': []}) is None

    with (
        patch('scripts.find_top_available.__file__', str(module_file)),
        patch('scripts.find_top_available.load_ros_rankings', return_value=[{'name': 'Player', 'position': 'QB', 'team': 'TST', 'rank': 1}]),
        patch('scripts.find_top_available.get_owned_players_by_league_with_teams', return_value=({}, {})),
    ):
        assert find_top_available_players({'leagues': []}) is None


def test_find_top_available_players_skips_leagues_without_roster_data(tmp_path):
    module_file = tmp_path / 'scripts' / 'find_top_available.py'
    module_file.parent.mkdir()
    module_file.write_text('', encoding='utf-8')
    output_dir = tmp_path / 'lineups'
    output_dir.mkdir()
    config = {'leagues': [{'league_name': 'Missing', 'team_name': 'Team'}]}

    with (
        patch('scripts.find_top_available.__file__', str(module_file)),
        patch('scripts.find_top_available.load_ros_rankings', return_value=[{'name': 'Player', 'position': 'QB', 'team': 'TST', 'rank': 1}]),
        patch('scripts.find_top_available.get_owned_players_by_league_with_teams', return_value=({'Other': set()}, {'Other': {}})),
    ):
        find_top_available_players(config)

    assert 'Missing' not in (output_dir / 'ros-analysis.md').read_text(encoding='utf-8')


def test_find_top_available_players_reports_output_error(tmp_path):
    module_file = tmp_path / 'scripts' / 'find_top_available.py'
    module_file.parent.mkdir()
    module_file.write_text('', encoding='utf-8')
    config = {'leagues': [{'league_name': 'League A', 'team_name': 'Team A'}]}
    data = {'League A': {'Player'}}
    with (
        patch('scripts.find_top_available.__file__', str(module_file)),
        patch('scripts.find_top_available.load_ros_rankings', return_value=[{'name': 'Player', 'position': 'QB', 'team': 'TST', 'rank': 1}]),
        patch('scripts.find_top_available.get_owned_players_by_league_with_teams', return_value=(data, {'League A': {'Team A': []}})),
        patch('builtins.open', side_effect=OSError('read-only')),
    ):
        find_top_available_players(config)
