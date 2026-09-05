import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import scripts.output_rankings as output_rankings_mod
from scripts.output_rankings import (
    find_player_ranking,
    get_available_players_by_position,
    get_team_players,
    load_custom_owned_players,
    load_rankings,
    main,
    organize_by_position,
    output_rankings,
    print_combined_position_rankings,
    safe_print,
    save_markdown,
)


def test_load_custom_owned_players_list(tmp_path):
    p = tmp_path / 'custom.json'
    p.write_text('["Player One", "Marvin Harrison Jr."]', encoding='utf-8')
    result = load_custom_owned_players(p)
    assert 'Player One' in result
    assert 'Marvin Harrison Jr.' in result
    assert 'marvin harrison' in result


def test_load_custom_owned_players_dict_owned_list(tmp_path):
    p = tmp_path / 'custom_dict.json'
    p.write_text('{"owned": ["Player A", "Player B"]}', encoding='utf-8')
    result = load_custom_owned_players(p)
    assert 'Player A' in result
    assert 'Player B' in result


def test_load_custom_owned_players_dict_teams(tmp_path):
    p = tmp_path / 'custom_teams.json'
    data = {
        'Team 1': ['Player X', {'name': 'Player Y'}],
        'Team 2': [{'name': 'Player Z'}],
    }
    p.write_text(json.dumps(data), encoding='utf-8')
    result = load_custom_owned_players(p)
    assert 'Player X' in result
    assert 'Player Y' in result
    assert 'Player Z' in result


def test_load_custom_owned_players_errors(tmp_path):
    assert load_custom_owned_players(tmp_path / 'missing.json') == set()
    bad_json = tmp_path / 'bad.json'
    bad_json.write_text('{ bad }', encoding='utf-8')
    assert load_custom_owned_players(bad_json) == set()


def test_load_custom_owned_players_resolves_relative_path(tmp_path):
    custom_file = tmp_path / 'custom.json'
    custom_file.write_text('["Player One"]', encoding='utf-8')
    with patch('scripts.output_rankings.BASE_DIR', tmp_path):
        assert load_custom_owned_players('custom.json') == {'Player One'}


def test_get_team_players():
    data = {'Team 1': [{'name': 'P1'}], 'Team 2': [{'name': 'P2'}]}
    assert get_team_players(data, 'Team 1') == [{'name': 'P1'}]
    assert get_team_players(data, 'Team NonExistent') is None
    assert get_team_players(None, 'Team 1') is None


def test_organize_by_position():
    espn_players = [
        {'name': 'Josh Allen', 'position': 'QB', 'proTeam': 'BUF', 'injured': False, 'totalPoints': 100.0},
        {'name': 'Saquon Barkley', 'position': 'RB', 'proTeam': 'PHI', 'injured': True, 'totalPoints': 80.0},
    ]
    organized = organize_by_position(espn_players, league_type='espn')
    assert len(organized['QB']) == 1
    assert organized['QB'][0]['proTeam'] == 'BUF'
    assert organized['RB'][0]['injured'] is True

    sleeper_players = [
        {'name': 'Josh Allen', 'position': 'QB', 'nfl_team': 'BUF', 'injured': False, 'totalPoints': 100.0},
    ]
    organized_sleeper = organize_by_position(sleeper_players, league_type='sleeper')
    assert organized_sleeper['QB'][0]['proTeam'] == 'BUF'


def test_load_rankings(tmp_path):
    qb_csv = tmp_path / 'qb.csv'
    qb_csv.write_text('Rank,Player Name,Team,Position\n1,Josh Allen,BUF,QB\n', encoding='utf-8')

    flex_csv = tmp_path / 'half_flex.csv'
    flex_csv.write_text('Rank,Player Name,Team,Position\n1,Saquon Barkley,PHI,RB\n', encoding='utf-8')

    dst_csv = tmp_path / 'dst.csv'
    dst_csv.write_text('Rank,Player Name,Team,Position\n1,San Francisco 49ers,SF,DST\n', encoding='utf-8')

    kicker_csv = tmp_path / 'kicker.csv'
    kicker_csv.write_text('Rank,Player Name,Team,Position\n1,Justin Tucker,BAL,K\n', encoding='utf-8')

    with patch('scripts.output_rankings.RANKINGS_DIR', tmp_path):
        rankings = load_rankings('half')
        assert 'QB' in rankings
        assert 'Josh Allen' in rankings['QB']
        assert 'RB' in rankings
        assert 'Saquon Barkley' in rankings['RB']
        assert 'D/ST' in rankings
        assert 'K' in rankings


def test_load_rankings_handles_missing_file_and_d_st_normalization(tmp_path):
    dst_csv = tmp_path / 'dst.csv'
    dst_csv.write_text('Rank,Player Name,Team,Position\n1,San Francisco 49ers,SF,DST\n', encoding='utf-8')
    with patch('scripts.output_rankings.RANKINGS_DIR', tmp_path):
        rankings = load_rankings('half')
    assert rankings['D/ST']['San Francisco 49ers D/ST']['position'] == 'D/ST'


def test_find_player_ranking_returns_none_for_unknown_position():
    assert find_player_ranking('Unknown', 'QB', {}) is None


def test_find_player_ranking():
    rankings = {
        'QB': {'Josh Allen': {'rank': 1, 'team': 'BUF', 'position': 'QB', 'player_name': 'Josh Allen'}},
        'D/ST': {
            'San Francisco 49ers D/ST': {
                'rank': 1,
                'team': 'SF',
                'position': 'D/ST',
                'player_name': 'San Francisco 49ers D/ST',
            }
        },
        'WR': {
            'Marvin Harrison': {
                'rank': 10,
                'team': 'ARI',
                'position': 'WR',
                'player_name': 'Marvin Harrison',
            }
        },
    }

    assert find_player_ranking('Josh Allen', 'QB', rankings)['rank'] == 1
    assert find_player_ranking('Unknown', 'QB', rankings) is None
    assert find_player_ranking('Josh Allen', 'K', rankings) is None
    # D/ST variations
    assert find_player_ranking('San Francisco 49ers', 'D/ST', rankings)['rank'] == 1
    assert find_player_ranking('SF D/ST', 'D/ST', rankings)['rank'] == 1
    # Fuzzy match
    assert find_player_ranking('Marvin Harrison Jr.', 'WR', rankings)['rank'] == 10


def test_get_available_players_by_position():
    rankings = {
        'QB': {
            'Josh Allen': {'rank': 1, 'team': 'BUF', 'position': 'QB'},
            'Patrick Mahomes': {'rank': 2, 'team': 'KC', 'position': 'QB'},
        }
    }
    all_owned = {'Josh Allen'}
    available = get_available_players_by_position(rankings, all_owned)
    assert len(available['QB']) == 1
    assert available['QB'][0]['name'] == 'Patrick Mahomes'


def test_safe_print_and_save_markdown(tmp_path):
    output_rankings_mod.markdown_content = []
    safe_print('# Test Title')
    safe_print('Test Content')

    out_file = tmp_path / 'lineups' / 'start-sit.md'

    def fake_path(p):
        if str(p) == output_rankings_mod.__file__:
            mock_obj = MagicMock()
            mock_obj.parent.parent = tmp_path
            return mock_obj
        return Path(p)

    with patch('scripts.output_rankings.Path', side_effect=fake_path):
        save_markdown()

    assert out_file.exists()
    content = out_file.read_text(encoding='utf-8')
    assert '# Test Title' in content
    assert 'Test Content' in content


def test_print_combined_position_rankings():
    output_rankings_mod.markdown_content = []
    players_by_position = {
        'QB': [{'name': 'Josh Allen', 'proTeam': 'BUF', 'injured': False, 'totalPoints': 20.0}],
        'RB': [{'name': 'Saquon Barkley', 'proTeam': 'PHI', 'injured': False, 'totalPoints': 15.0}],
    }
    all_owned_players = {'Josh Allen', 'Saquon Barkley'}
    rankings = {
        'QB': {
            'Josh Allen': {'rank': 1, 'team': 'BUF', 'position': 'QB', 'player_name': 'Josh Allen'},
            'Lamar Jackson': {'rank': 2, 'team': 'BAL', 'position': 'QB', 'player_name': 'Lamar Jackson'},
        },
        'RB': {
            'Saquon Barkley': {'rank': 1, 'team': 'PHI', 'position': 'RB', 'player_name': 'Saquon Barkley'},
            'Breece Hall': {'rank': 2, 'team': 'NYJ', 'position': 'RB', 'player_name': 'Breece Hall'},
        },
        'WR': {},
        'TE': {},
        'D/ST': {},
        'K': {},
    }

    print_combined_position_rankings(players_by_position, all_owned_players, rankings, 'My Team', 'My League')
    output_text = '\n'.join(output_rankings_mod.markdown_content)
    assert '### COMBINED RANKINGS: MY LEAGUE MY TEAM' in output_text
    assert 'Josh Allen' in output_text
    assert 'Lamar Jackson' in output_text
    assert '🏆 Team' in output_text
    assert '⚡ Free' in output_text


def test_print_combined_position_rankings_includes_unranked_players():
    output_rankings_mod.markdown_content = []
    players = {
        'WR': [{'name': 'Unranked', 'proTeam': 'FA', 'totalPoints': 12.0}],
    }
    print_combined_position_rankings(players, set(), {'WR': {}}, 'Team', 'League')
    output = '\n'.join(output_rankings_mod.markdown_content)
    assert '| Unranked | FA | WR | 12.0 |' in output


def test_output_rankings_custom_file_and_missing_rankings(tmp_path):
    owned_file = tmp_path / 'espn_123_owned_players.json'
    owned_file.write_text(json.dumps({'Team A': []}), encoding='utf-8')
    custom_file = tmp_path / 'custom.json'
    custom_file.write_text('["Player A"]', encoding='utf-8')
    with (
        patch('scripts.output_rankings.ROSTERS_DIR', tmp_path),
        patch('scripts.output_rankings.load_rankings', return_value={}),
    ):
        assert output_rankings('Team A', 'half', 'espn', 'espn_123', 'League', custom_file) is False


def test_save_markdown_reports_write_error():
    with patch('scripts.output_rankings.open', side_effect=OSError('read-only')):
        output_rankings_mod.save_markdown()


def test_output_main_handles_empty_and_invalid_leagues():
    with patch('scripts.output_rankings.load_league_config', return_value=None):
        output_rankings_mod.main()
    with patch('scripts.output_rankings.load_league_config', return_value={'leagues': []}):
        output_rankings_mod.main()


def test_output_main_processes_multiple_leagues_and_failures():
    config = {
        'leagues': [
            {'team_name': 'Missing', 'scoring_type': 'half'},
            {'team_name': 'Team A', 'scoring_type': 'half', 'league_id': '1', 'platform': 'espn'},
            {'team_name': 'Team B', 'scoring_type': 'half', 'league_id': '2', 'platform': 'espn'},
        ]
    }
    with (
        patch('scripts.output_rankings.load_league_config', return_value=config),
        patch('scripts.output_rankings.output_rankings', side_effect=[False, True]),
        patch('scripts.output_rankings.save_markdown'),
    ):
        output_rankings_mod.main()


def test_output_rankings_flow(tmp_path):
    output_rankings_mod.markdown_content = []
    owned_file = tmp_path / 'espn_123_owned_players.json'
    owned_file.write_text(
        json.dumps(
            {
                'Team A': [
                    {'name': 'Josh Allen', 'position': 'QB', 'proTeam': 'BUF', 'injured': False, 'totalPoints': 10.0}
                ]
            }
        ),
        encoding='utf-8',
    )

    rankings = {
        'QB': {'Josh Allen': {'rank': 1, 'team': 'BUF', 'position': 'QB', 'player_name': 'Josh Allen'}},
        'RB': {},
        'WR': {},
        'TE': {},
        'D/ST': {},
        'K': {},
    }

    with (
        patch('scripts.output_rankings.ROSTERS_DIR', tmp_path),
        patch('scripts.output_rankings.load_rankings', return_value=rankings),
    ):
        res = output_rankings('Team A', 'half', 'espn', 'espn_123', 'Test League')
        assert res is True


def test_output_rankings_missing_data(tmp_path):
    with patch('scripts.output_rankings.ROSTERS_DIR', tmp_path):
        res = output_rankings('Team A', 'half', 'espn', 'espn_missing', 'Test League')
        assert res is False


def test_output_rankings_missing_rankings(tmp_path):
    owned_file = tmp_path / 'espn_123_owned_players.json'
    owned_file.write_text(json.dumps({'Team A': []}), encoding='utf-8')
    with (
        patch('scripts.output_rankings.ROSTERS_DIR', tmp_path),
        patch('scripts.output_rankings.load_rankings', return_value={}),
    ):
        res = output_rankings('Team A', 'half', 'espn', 'espn_123', 'Test League')
        assert res is False


def test_main_flow(tmp_path):
    config = {
        'leagues': [
            {'team_name': 'Team A', 'scoring_type': 'half', 'league_id': '123', 'platform': 'espn'},
            {'team_name': 'Team Incomplete'},  # missing required fields
        ]
    }
    with (
        patch('scripts.output_rankings.load_league_config', return_value=config),
        patch('scripts.output_rankings.output_rankings', return_value=True) as mock_out,
        patch('scripts.output_rankings.save_markdown'),
    ):
        main()
        assert mock_out.call_count == 1
