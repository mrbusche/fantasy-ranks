import json
from unittest.mock import MagicMock, patch

import pytest

from fantasy_ranks.fetch_yahoo_transactions import (
    build_transactions_url,
    fetch_yahoo_transactions,
    main,
    update_yahoo_league,
)

SAMPLE_HTML = """
<html><body>
<table>
<tr><td>Added Player</td><td>SF - TE</td></tr>
<tr><td>Waiver</td></tr>
<tr><td>Team Alpha</td></tr>
<tr><td>Sep 4, 8:00 pm</td></tr>
</table>
</body></html>
"""


def test_build_transactions_url():
    assert build_transactions_url('960067') == 'https://football.fantasysports.yahoo.com/f1/960067/transactions'


def test_fetch_yahoo_transactions_requires_cookie(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('fantasy_ranks.yahoo_web.YAHOO_COOKIE', None)

    with pytest.raises(RuntimeError, match='YAHOO_COOKIE'):
        fetch_yahoo_transactions('960067')


def test_fetch_yahoo_transactions_saves_text(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('fantasy_ranks.yahoo_web.YAHOO_COOKIE', 'fake-cookie')
    monkeypatch.setattr('fantasy_ranks.fetch_yahoo_transactions.ROSTERS_DIR', tmp_path / 'rosters')

    response = MagicMock()
    response.text = SAMPLE_HTML
    response.raise_for_status.return_value = None

    with patch('fantasy_ranks.yahoo_web.requests.get', return_value=response) as mock_get:
        output_path = fetch_yahoo_transactions('960067')
        mock_get.assert_called_once()

    saved_text = open(output_path, encoding='utf-8').read()
    assert saved_text.splitlines() == [
        'Added Player\tSF - TE',
        'Waiver',
        'Team Alpha',
        'Sep 4, 8:00 pm',
    ]


def test_update_yahoo_league_imports_draft_when_no_owned_players_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('fantasy_ranks.yahoo_web.YAHOO_COOKIE', 'fake-cookie')
    rosters_dir = tmp_path / 'rosters'
    monkeypatch.setattr('fantasy_ranks.fetch_yahoo_transactions.ROSTERS_DIR', rosters_dir)
    monkeypatch.setattr('fantasy_ranks.fetch_yahoo_draft.ROSTERS_DIR', rosters_dir)

    response = MagicMock()
    response.text = SAMPLE_HTML
    response.raise_for_status.return_value = None

    with (
        patch('fantasy_ranks.yahoo_web.requests.get', return_value=response),
        patch('fantasy_ranks.fetch_yahoo_transactions.apply_yahoo_updates') as mock_apply,
    ):
        update_yahoo_league('960067')
        mock_apply.assert_called_once_with('960067')

    assert 'does not exist yet - importing the draft first' in capsys.readouterr().out
    assert (rosters_dir / 'yahoo_960067.txt').exists()
    assert (rosters_dir / 'yahoo_960067_owned_players.json').exists()


def test_update_yahoo_league_applies_updates_when_owned_players_file_exists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('fantasy_ranks.yahoo_web.YAHOO_COOKIE', 'fake-cookie')
    rosters_dir = tmp_path / 'rosters'
    rosters_dir.mkdir()
    monkeypatch.setattr('fantasy_ranks.fetch_yahoo_transactions.ROSTERS_DIR', rosters_dir)

    owned_players_file = rosters_dir / 'yahoo_960067_owned_players.json'
    owned_players_file.write_text(json.dumps({'Team Alpha': []}), encoding='utf-8')

    response = MagicMock()
    response.text = SAMPLE_HTML
    response.raise_for_status.return_value = None

    with (
        patch('fantasy_ranks.yahoo_web.requests.get', return_value=response),
        patch('fantasy_ranks.fetch_yahoo_transactions.apply_yahoo_updates') as mock_apply,
    ):
        update_yahoo_league('960067')
        mock_apply.assert_called_once_with('960067')


def test_main_calls_update_yahoo_league(monkeypatch):
    monkeypatch.setattr('sys.argv', ['fetch_yahoo_transactions', '960067'])
    with patch('fantasy_ranks.fetch_yahoo_transactions.update_yahoo_league') as mock_update:
        main()
        mock_update.assert_called_once_with('960067')
