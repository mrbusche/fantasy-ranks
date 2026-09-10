import json

from fantasy_ranks.update_yahoo_rosters import apply_yahoo_updates, parse_transaction_row


def test_parse_transaction_row_add_and_drop_swap():
    row = ' \tT.J. Hockenson Min - TE Free Agent Dalton Kincaid Buf - TE To Waivers\tRunitback Sep 9, 4:51 pm'
    assert parse_transaction_row(row) == (
        'Runitback',
        {'name': 'T.J. Hockenson', 'position': 'TE'},
        'Dalton Kincaid',
    )


def test_parse_transaction_row_add_only():
    row = ' \tMichael Mayer LV - TE Free Agent\tThe Sheriff Sep 9, 4:42 pm'
    assert parse_transaction_row(row) == ('The Sheriff', {'name': 'Michael Mayer', 'position': 'TE'}, None)


def test_parse_transaction_row_drop_only():
    row = ' \tDalton Kincaid Buf - TE To Waivers\tRunitback Sep 9, 4:51 pm'
    assert parse_transaction_row(row) == ('Runitback', None, 'Dalton Kincaid')


def test_parse_transaction_row_ignores_non_transaction_rows():
    assert parse_transaction_row('Added Players') is None
    assert parse_transaction_row('Team Alpha') is None


def test_apply_yahoo_updates_processes_transactions_oldest_first(tmp_path, monkeypatch):
    rosters_dir = tmp_path / 'rosters'
    rosters_dir.mkdir()
    (rosters_dir / 'yahoo_123_owned_players.json').write_text(
        json.dumps({'Team Alpha': []}),
        encoding='utf-8',
    )
    # Yahoo! lists the newest transaction first, so the drop (Sep 3) appears before the add (Sep 2).
    transactions = '\n'.join(
        [
            ' \tNew Player KC - RB To Waivers\tTeam Alpha Sep 3, 10:14 pm',
            ' \tNew Player KC - RB Waiver\tTeam Alpha Sep 2, 10:14 pm',
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
            ' \tDropped Player NYG - WR To Waivers\tTeam Alpha Sep 5, 8:00 pm',
            ' \tAdded Player SF - TE Waiver\tTeam Alpha Sep 4, 8:00 pm',
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


def test_apply_yahoo_updates_swap_transaction(tmp_path, monkeypatch):
    rosters_dir = tmp_path / 'rosters'
    rosters_dir.mkdir()
    (rosters_dir / 'yahoo_999_owned_players.json').write_text(
        json.dumps({'Runitback': [{'name': 'Dalton Kincaid', 'position': 'TE'}]}),
        encoding='utf-8',
    )
    transactions = ' \tT.J. Hockenson Min - TE Free Agent Dalton Kincaid Buf - TE To Waivers\tRunitback Sep 9, 4:51 pm'
    (rosters_dir / 'yahoo_updates_999.txt').write_text(transactions, encoding='utf-8')
    monkeypatch.chdir(tmp_path)

    apply_yahoo_updates('999')

    assert json.loads((rosters_dir / 'yahoo_999_owned_players.json').read_text(encoding='utf-8')) == {
        'Runitback': [{'name': 'T.J. Hockenson', 'position': 'TE'}],
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
            ' \tUnknown Player DAL - WR Waiver\tTeam Beta Sep 6, 8:00 pm',
            ' \tExisting Player JAX - RB Waiver\tTeam Alpha Sep 5, 8:00 pm',
        ]
    )
    (rosters_dir / 'yahoo_updates_789.txt').write_text(transactions, encoding='utf-8')
    monkeypatch.chdir(tmp_path)

    apply_yahoo_updates('789')

    assert json.loads((rosters_dir / 'yahoo_789_owned_players.json').read_text(encoding='utf-8')) == {
        'Team Alpha': [{'name': 'Existing Player', 'position': 'RB'}]
    }


def test_apply_yahoo_updates_ignores_non_transaction_lines(tmp_path, monkeypatch):
    rosters_dir = tmp_path / 'rosters'
    rosters_dir.mkdir()
    (rosters_dir / 'yahoo_321_owned_players.json').write_text(
        json.dumps({'Team Alpha': []}),
        encoding='utf-8',
    )
    transactions = '\n'.join(
        [
            'Recent Transactions',
            'All Teams',
            'Team Alpha',
            'Added Players',
            'Dropped Players',
            'Trades',
            'Waiver Offers',
            ' \tAdded Player SF - TE Waiver\tTeam Alpha Sep 4, 8:00 pm',
        ]
    )
    (rosters_dir / 'yahoo_updates_321.txt').write_text(transactions, encoding='utf-8')
    monkeypatch.chdir(tmp_path)

    apply_yahoo_updates('321')

    assert json.loads((rosters_dir / 'yahoo_321_owned_players.json').read_text(encoding='utf-8')) == {
        'Team Alpha': [{'name': 'Added Player', 'position': 'TE'}]
    }
