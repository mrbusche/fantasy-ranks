import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import fantasy_ranks.output_rankings as output_rankings_mod
from fantasy_ranks.output_rankings import (
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
    with patch('fantasy_ranks.output_rankings.BASE_DIR', tmp_path):
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

    yahoo_players = [{'name': 'Chargers', 'position': 'DEF'}]
    organized_yahoo = organize_by_position(yahoo_players, league_type='yahoo')
    assert len(organized_yahoo['D/ST']) == 1


def test_load_rankings(tmp_path):
    qb_csv = tmp_path / 'qb.csv'
    qb_csv.write_text('Rank,Player Name,Team,Position\n1,Josh Allen,BUF,QB\n', encoding='utf-8')

    flex_csv = tmp_path / 'half_flex.csv'
    flex_csv.write_text('Rank,Player Name,Team,Position\n1,Saquon Barkley,PHI,RB\n', encoding='utf-8')

    dst_csv = tmp_path / 'dst.csv'
    dst_csv.write_text('Rank,Player Name,Team,Position\n1,San Francisco 49ers,SF,DST\n', encoding='utf-8')

    kicker_csv = tmp_path / 'kicker.csv'
    kicker_csv.write_text('Rank,Player Name,Team,Position\n1,Justin Tucker,BAL,K\n', encoding='utf-8')

    with patch('fantasy_ranks.output_rankings.RANKINGS_DIR', tmp_path):
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
    with patch('fantasy_ranks.output_rankings.RANKINGS_DIR', tmp_path):
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
            mock_obj.resolve.return_value = mock_obj
            mock_obj.parent.parent.parent = tmp_path
            return mock_obj
        return Path(p)

    with patch('fantasy_ranks.output_rankings.Path', side_effect=fake_path):
        save_markdown()

    assert out_file.exists()
    content = out_file.read_text(encoding='utf-8')
    assert '# Test Title' in content
    assert 'Test Content' in content


def test_print_combined_position_rankings_optimal_and_header():
    output_rankings_mod.markdown_content = []
    players_by_position = {
        'QB': [{'name': 'Josh Allen', 'proTeam': 'BUF', 'injured': False, 'totalPoints': 20.0}],
    }
    all_owned_players = {'Josh Allen'}
    rankings = {
        'QB': {
            'Josh Allen': {'rank': 1, 'team': 'BUF', 'position': 'QB', 'player_name': 'Josh Allen'},
            'Lamar Jackson': {'rank': 2, 'team': 'BAL', 'position': 'QB', 'player_name': 'Lamar Jackson'},
        },
        'RB': {},
        'WR': {},
        'TE': {},
        'D/ST': {},
        'K': {},
    }

    print_combined_position_rankings(players_by_position, all_owned_players, rankings, 'My Team', 'My League')
    output_text = '\n'.join(output_rankings_mod.markdown_content)
    assert '### My League My Team — Starting Roster' in output_text
    # Josh Allen (QB1) is better ranked than the best available FA Lamar Jackson (QB2) - Optimal.
    assert '| QB | Josh Allen (QB) | QB1 | Lamar Jackson (QB - BAL) | QB2 | Optimal |' in output_text
    assert '### Top 5 Available Players by Position' in output_text
    assert '#### Quarterbacks (QB)' in output_text
    assert '| Lamar Jackson (QB - BAL) | QB2 |' in output_text


def test_print_combined_position_rankings_free_agent_better_and_flex():
    output_rankings_mod.markdown_content = []
    players_by_position = {
        'RB': [
            {'name': 'Saquon Barkley', 'proTeam': 'PHI', 'injured': False, 'totalPoints': 15.0},
            {'name': 'Bench RB', 'proTeam': 'NYJ', 'injured': False, 'totalPoints': 5.0},
        ],
    }
    all_owned_players = {'Saquon Barkley', 'Bench RB'}
    rankings = {
        'QB': {},
        'RB': {
            'Saquon Barkley': {'rank': 1, 'team': 'PHI', 'position': 'RB', 'player_name': 'Saquon Barkley'},
            'Bench RB': {'rank': 5, 'team': 'NYJ', 'position': 'RB', 'player_name': 'Bench RB'},
        },
        'WR': {},
        'TE': {},
        'D/ST': {},
        'K': {},
    }

    # This league only starts 1 RB and 1 FLEX; the bench RB should fill FLEX since there
    # is no better available free agent, and the FLEX slot should show both ranks.
    print_combined_position_rankings(
        players_by_position,
        all_owned_players,
        rankings,
        'My Team',
        'My League',
        lineup_slots={'RB': 1, 'FLEX': 1},
    )
    output_text = '\n'.join(output_rankings_mod.markdown_content)
    assert '| RB | Saquon Barkley (RB) | RB1 | — | — | No Free Agents Available |' in output_text
    assert '| FLEX | Bench RB (RB) | RB2 / FLEX 5 | — | — | No Free Agents Available |' in output_text


def test_print_combined_position_rankings_unranked_and_empty_slot():
    output_rankings_mod.markdown_content = []
    players_by_position = {
        'QB': [{'name': 'Undrafted QB', 'proTeam': 'FA', 'injured': False, 'totalPoints': 3.0}],
    }
    all_owned_players = {'Undrafted QB'}
    rankings = {
        'QB': {},
        'RB': {},
        'WR': {},
        'TE': {},
        'D/ST': {},
        'K': {},
    }

    # Two QB starter slots but only one (unranked) rostered QB - the second slot is empty.
    print_combined_position_rankings(
        players_by_position, all_owned_players, rankings, 'My Team', 'My League', lineup_slots={'QB': 2}
    )
    output_text = '\n'.join(output_rankings_mod.markdown_content)
    assert '| QB | Undrafted QB (QB) | — | — | — | Unranked |' in output_text
    assert '| QB | — (Empty Slot) | — | — | — | No Player Rostered |' in output_text


def test_print_combined_position_rankings_zero_starter_row():
    output_rankings_mod.markdown_content = []
    players_by_position = {
        'QB': [{'name': 'Starter QB', 'proTeam': 'BUF', 'injured': False, 'totalPoints': 20.0}],
    }
    all_owned_players = {'Starter QB'}
    rankings = {
        'QB': {'Starter QB': {'rank': 1, 'team': 'BUF', 'position': 'QB', 'player_name': 'Starter QB'}},
        'RB': {},
        'WR': {},
        'TE': {},
        'D/ST': {},
        'K': {},
    }

    # This league doesn't use kickers or defense at all - both rows should be omitted.
    print_combined_position_rankings(
        players_by_position,
        all_owned_players,
        rankings,
        'My Team',
        'My League',
        lineup_slots={'QB': 1, 'RB': 0, 'WR': 0, 'TE': 0, 'FLEX': 0, 'K': 0, 'D/ST': 0},
    )
    output_text = '\n'.join(output_rankings_mod.markdown_content)
    assert '| K |' not in output_text
    assert '| D/ST |' not in output_text


def test_print_combined_position_rankings_superflex():
    output_rankings_mod.markdown_content = []
    players_by_position = {
        'QB': [
            {'name': 'Starter QB', 'proTeam': 'BUF', 'injured': False, 'totalPoints': 20.0},
            {'name': 'Backup QB', 'proTeam': 'NYJ', 'injured': False, 'totalPoints': 10.0},
        ],
    }
    all_owned_players = {'Starter QB', 'Backup QB'}
    rankings = {
        'QB': {
            'Starter QB': {'rank': 1, 'team': 'BUF', 'position': 'QB', 'player_name': 'Starter QB'},
            'Backup QB': {'rank': 5, 'team': 'NYJ', 'position': 'QB', 'player_name': 'Backup QB'},
            'FA QB': {'rank': 8, 'team': 'FA', 'position': 'QB', 'player_name': 'FA QB'},
        },
        'RB': {},
        'WR': {},
        'TE': {},
        'D/ST': {},
        'K': {},
    }

    # Only 1 QB slot is needed, so Backup QB should fill the SUPERFLEX slot using the raw rank.
    print_combined_position_rankings(
        players_by_position,
        all_owned_players,
        rankings,
        'My Team',
        'My League',
        lineup_slots={'QB': 1, 'FLEX': 0, 'SUPERFLEX': 1, 'RB': 0, 'WR': 0, 'TE': 0, 'K': 0, 'D/ST': 0},
    )
    output_text = '\n'.join(output_rankings_mod.markdown_content)
    assert '| SUPERFLEX | Backup QB (QB) | #5 | FA QB (QB - FA) | #8 | Optimal |' in output_text
    assert '#### Superflex (QB/RB/WR/TE)' in output_text


def test_print_combined_position_rankings_shows_bench():
    output_rankings_mod.markdown_content = []
    players_by_position = {
        'QB': [
            {'name': 'Starter QB', 'proTeam': 'BUF', 'injured': False, 'totalPoints': 20.0},
            {'name': 'Backup QB', 'proTeam': 'NYJ', 'injured': False, 'totalPoints': 5.0},
        ],
        'RB': [
            {'name': 'Starter RB', 'proTeam': 'PHI', 'injured': False, 'totalPoints': 15.0},
            {'name': 'Backup RB', 'proTeam': 'NYJ', 'injured': False, 'totalPoints': 5.0},
        ],
        'WR': [
            {'name': 'Flex Rank 102', 'proTeam': 'NYJ', 'injured': False, 'totalPoints': 5.0},
            {'name': 'Flex Rank 59', 'proTeam': 'PHI', 'injured': False, 'totalPoints': 5.0},
        ],
    }
    all_owned_players = {'Starter QB', 'Backup QB', 'Starter RB', 'Backup RB', 'Flex Rank 102', 'Flex Rank 59'}
    rankings = {
        'QB': {
            'Starter QB': {'rank': 1, 'team': 'BUF', 'position': 'QB', 'player_name': 'Starter QB'},
            'Backup QB': {'rank': 12, 'team': 'NYJ', 'position': 'QB', 'player_name': 'Backup QB'},
        },
        'RB': {
            'Starter RB': {'rank': 1, 'team': 'PHI', 'position': 'RB', 'player_name': 'Starter RB'},
            'Backup RB': {'rank': 12, 'team': 'NYJ', 'position': 'RB', 'player_name': 'Backup RB'},
        },
        'WR': {
            'Flex Rank 102': {'rank': 102, 'team': 'NYJ', 'position': 'WR', 'player_name': 'Flex Rank 102'},
            'Flex Rank 59': {'rank': 59, 'team': 'PHI', 'position': 'WR', 'player_name': 'Flex Rank 59'},
        },
        'TE': {},
        'D/ST': {},
        'K': {},
    }

    # Only 1 QB and 1 RB slot are needed, and there is no FLEX, so Backup QB stays on the bench.
    print_combined_position_rankings(
        players_by_position,
        all_owned_players,
        rankings,
        'My Team',
        'My League',
        lineup_slots={'QB': 1, 'RB': 1, 'WR': 0, 'FLEX': 0},
    )
    output_text = '\n'.join(output_rankings_mod.markdown_content)
    assert '### Bench' in output_text
    assert '| Backup QB (QB) | QB2 |' in output_text
    assert '| Backup RB (RB) | RB2 / FLEX 12 |' in output_text
    bench_section = output_text.split('### Bench')[1].split('### Top')[0]
    assert bench_section.index('Flex Rank 59') < bench_section.index('Flex Rank 102')
    assert 'Starter QB (QB)' not in output_text.split('### Bench')[1].split('### Top')[0]


def test_print_combined_position_rankings_matches_bench_name_suffix():
    output_rankings_mod.markdown_content = []
    players_by_position = {
        'QB': [{'name': 'Patrick Mahomes', 'proTeam': 'KC', 'injured': False, 'totalPoints': 5.0}],
    }
    rankings = {
        'QB': {
            'Patrick Mahomes II': {
                'rank': 21,
                'team': 'KC',
                'position': 'QB',
                'player_name': 'Patrick Mahomes II',
            }
        },
        'RB': {},
        'WR': {},
        'TE': {},
        'D/ST': {},
        'K': {},
    }

    print_combined_position_rankings(
        players_by_position,
        {'Patrick Mahomes'},
        rankings,
        'My Team',
        'My League',
        lineup_slots={'QB': 0, 'FLEX': 0},
    )
    output_text = '\n'.join(output_rankings_mod.markdown_content)
    assert '| Patrick Mahomes (QB) | QB1 |' in output_text


def test_print_combined_position_rankings_empty_bench_message():
    output_rankings_mod.markdown_content = []
    players_by_position = {
        'QB': [{'name': 'Only QB', 'proTeam': 'BUF', 'injured': False, 'totalPoints': 20.0}],
    }
    all_owned_players = {'Only QB'}
    rankings = {
        'QB': {'Only QB': {'rank': 1, 'team': 'BUF', 'position': 'QB', 'player_name': 'Only QB'}},
        'RB': {},
        'WR': {},
        'TE': {},
        'D/ST': {},
        'K': {},
    }

    print_combined_position_rankings(
        players_by_position, all_owned_players, rankings, 'My Team', 'My League', lineup_slots={'QB': 1, 'FLEX': 0}
    )
    output_text = '\n'.join(output_rankings_mod.markdown_content)
    bench_section = output_text.split('### Bench')[1].split('### Top')[0]
    assert 'No bench players found.' in bench_section


def test_output_rankings_custom_file_and_missing_rankings(tmp_path):
    owned_file = tmp_path / 'espn_123_owned_players.json'
    owned_file.write_text(json.dumps({'Team A': []}), encoding='utf-8')
    custom_file = tmp_path / 'custom.json'
    custom_file.write_text('["Player A"]', encoding='utf-8')
    with (
        patch('fantasy_ranks.output_rankings.ROSTERS_DIR', tmp_path),
        patch('fantasy_ranks.output_rankings.load_rankings', return_value={}),
    ):
        assert output_rankings('Team A', 'half', 'espn', 'espn_123', 'League', custom_file) is False


def test_save_markdown_reports_write_error():
    with patch('fantasy_ranks.output_rankings.open', side_effect=OSError('read-only')):
        output_rankings_mod.save_markdown()


def test_output_main_handles_empty_and_invalid_leagues():
    with patch('fantasy_ranks.output_rankings.load_league_config', return_value=None):
        output_rankings_mod.main()
    with patch('fantasy_ranks.output_rankings.load_league_config', return_value={'leagues': []}):
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
        patch('fantasy_ranks.output_rankings.load_league_config', return_value=config),
        patch('fantasy_ranks.output_rankings.output_rankings', side_effect=[False, True]),
        patch('fantasy_ranks.output_rankings.save_markdown'),
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
        patch('fantasy_ranks.output_rankings.ROSTERS_DIR', tmp_path),
        patch('fantasy_ranks.output_rankings.load_rankings', return_value=rankings),
    ):
        res = output_rankings('Team A', 'half', 'espn', 'espn_123', 'Test League')
        assert res is True


def test_output_rankings_missing_data(tmp_path):
    with patch('fantasy_ranks.output_rankings.ROSTERS_DIR', tmp_path):
        res = output_rankings('Team A', 'half', 'espn', 'espn_missing', 'Test League')
        assert res is False


def test_output_rankings_missing_rankings(tmp_path):
    owned_file = tmp_path / 'espn_123_owned_players.json'
    owned_file.write_text(json.dumps({'Team A': []}), encoding='utf-8')
    with (
        patch('fantasy_ranks.output_rankings.ROSTERS_DIR', tmp_path),
        patch('fantasy_ranks.output_rankings.load_rankings', return_value={}),
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
        patch('fantasy_ranks.output_rankings.load_league_config', return_value=config),
        patch('fantasy_ranks.output_rankings.output_rankings', return_value=True) as mock_out,
        patch('fantasy_ranks.output_rankings.save_markdown'),
    ):
        main()
        assert mock_out.call_count == 1
