import json

from fantasy_ranks.ownership import build_ownership_report, write_ownership_report


def test_build_ownership_report_uses_configured_team_only(tmp_path):
    rosters_dir = tmp_path / 'rosters'
    rosters_dir.mkdir()
    (rosters_dir / 'espn_123_owned_players.json').write_text(
        json.dumps(
            {
                'My Team': [{'name': 'Player One'}, {'name': 'Shared Player'}],
                'Other Team': [{'name': 'Other Player'}, {'name': 'Shared Player'}],
            }
        ),
        encoding='utf-8',
    )

    config = {
        'leagues': [
            {
                'platform': 'espn',
                'league_id': '123',
                'team_name': 'My Team',
                'league_name': 'Test League',
            }
        ]
    }

    assert build_ownership_report(config, rosters_dir) == [
        ('Player One', 1, 'Test League'),
        ('Shared Player', 1, 'Test League'),
    ]


def test_write_ownership_report_includes_league_list(tmp_path):
    rosters_dir = tmp_path / 'rosters'
    rosters_dir.mkdir()
    for league_id, league_name in [('123', 'First League'), ('456', 'Second League')]:
        (rosters_dir / f'espn_{league_id}_owned_players.json').write_text(
            json.dumps({'My Team': [{'name': 'Shared Player'}]}),
            encoding='utf-8',
        )

    config = {
        'leagues': [
            {'platform': 'espn', 'league_id': '123', 'team_name': 'My Team', 'league_name': 'First League'},
            {'platform': 'espn', 'league_id': '456', 'team_name': 'My Team', 'league_name': 'Second League'},
        ]
    }
    output_file = tmp_path / 'ownership.md'

    write_ownership_report(config, output_file, rosters_dir)

    assert output_file.read_text(encoding='utf-8') == (
        '# Player Ownership\n\n'
        'Players owned by the configured team in each league, grouped by ownership count.\n\n'
        '| Player Name | Owned Count | Leagues |\n'
        '| --- | ---: | --- |\n'
        '| Shared Player | 2 | First League<br>Second League |\n'
    )
