import json

from fantasy_ranks.update_yahoo_rosters import apply_yahoo_updates


def test_apply_yahoo_updates_processes_transactions_oldest_first(tmp_path, monkeypatch):
    rosters_dir = tmp_path / 'rosters'
    rosters_dir.mkdir()
    (rosters_dir / 'yahoo_123_owned_players.json').write_text(
        json.dumps({'Team Alpha': []}),
        encoding='utf-8',
    )
    transactions = '\n'.join(
        [
            'New Player KC - RB',
            'To Waivers',
            'Team Alpha',
            'Sep 3, 10:14 pm',
            'New Player KC - RB',
            'Waiver',
            'Team Alpha',
            'Sep 2, 10:14 pm',
        ]
    )
    (rosters_dir / 'yahoo_updates_123.txt').write_text(transactions, encoding='utf-8')
    monkeypatch.chdir(tmp_path)

    apply_yahoo_updates('123')

    assert json.loads((rosters_dir / 'yahoo_123_owned_players.json').read_text(encoding='utf-8')) == {
        'Team Alpha': [],
    }


def test_apply_yahoo_updates_adds_and_drops_players(tmp_path, monkeypatch):
    rosters_dir = tmp_path / 'rosters'
    rosters_dir.mkdir()
    (rosters_dir / 'yahoo_456_owned_players.json').write_text(
        json.dumps(
            {
                'Team Alpha': [
                    {'name': 'Dropped Player', 'position': 'WR'},
                    {'name': 'Existing Player', 'position': 'RB'},
                ]
            }
        ),
        encoding='utf-8',
    )
    transactions = '\n'.join(
        [
            'Added Player SF - TE',
            'Waiver',
            'Team Alpha',
            'Sep 4, 8:00 pm',
            'Dropped Player NYG - WR',
            'To Waivers',
            'Team Alpha',
            'Sep 5, 8:00 pm',
        ]
    )
    (rosters_dir / 'yahoo_updates_456.txt').write_text(transactions, encoding='utf-8')
    monkeypatch.chdir(tmp_path)

    apply_yahoo_updates('456')

    assert json.loads((rosters_dir / 'yahoo_456_owned_players.json').read_text(encoding='utf-8')) == {
        'Team Alpha': [
            {'name': 'Existing Player', 'position': 'RB'},
            {'name': 'Added Player', 'position': 'TE'},
        ]
    }


def test_apply_yahoo_updates_skips_unknown_teams_and_duplicate_players(tmp_path, monkeypatch):
    rosters_dir = tmp_path / 'rosters'
    rosters_dir.mkdir()
    (rosters_dir / 'yahoo_789_owned_players.json').write_text(
        json.dumps({'Team Alpha': [{'name': 'Existing Player', 'position': 'RB'}]}),
        encoding='utf-8',
    )
    transactions = '\n'.join(
        [
            'Unknown Player DAL - WR',
            'Waiver',
            'Team Beta',
            'Sep 6, 8:00 pm',
            'Existing Player JAX - RB',
            'Waiver',
            'Team Alpha',
            'Sep 5, 8:00 pm',
        ]
    )
    (rosters_dir / 'yahoo_updates_789.txt').write_text(transactions, encoding='utf-8')
    monkeypatch.chdir(tmp_path)

    apply_yahoo_updates('789')

    assert json.loads((rosters_dir / 'yahoo_789_owned_players.json').read_text(encoding='utf-8')) == {
        'Team Alpha': [{'name': 'Existing Player', 'position': 'RB'}]
    }
