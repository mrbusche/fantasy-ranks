import json

from fantasy_ranks.parse_yahoo_draft import parse_yahoo_draft


def test_parse_yahoo_draft_writes_players_by_team(tmp_path, monkeypatch):
    rosters_dir = tmp_path / 'rosters'
    rosters_dir.mkdir()
    draft_results = '\n'.join(
        [
            'Team Alpha',
            '1.\t(1)\tJosh Allen (Buf - QB)',
            '4. (4) Amon-Ra St. Brown (Det - WR)',
            'Team Beta',
            '1. (2) Christian McCaffrey (SF - RB)',
            '3. (3) Travis Kelce (KC - TE)',
        ]
    )
    (rosters_dir / 'yahoo_123.txt').write_text(draft_results, encoding='utf-8')
    monkeypatch.chdir(tmp_path)

    parse_yahoo_draft('123')

    output_file = rosters_dir / 'yahoo_123_owned_players.json'
    assert json.loads(output_file.read_text(encoding='utf-8')) == {
        'Team Alpha': [
            {'name': 'Josh Allen', 'position': 'QB'},
            {'name': 'Amon-Ra St. Brown', 'position': 'WR'},
        ],
        'Team Beta': [
            {'name': 'Christian McCaffrey', 'position': 'RB'},
            {'name': 'Travis Kelce', 'position': 'TE'},
        ],
    }


def test_parse_yahoo_draft_ignores_content_without_valid_picks(tmp_path, monkeypatch):
    rosters_dir = tmp_path / 'rosters'
    rosters_dir.mkdir()
    (rosters_dir / 'yahoo_456.txt').write_text(
        'Draft Results\nTeam Alpha\nNot a draft pick\n', encoding='utf-8'
    )
    monkeypatch.chdir(tmp_path)

    parse_yahoo_draft('456')

    output_file = rosters_dir / 'yahoo_456_owned_players.json'
    assert json.loads(output_file.read_text(encoding='utf-8')) == {}
