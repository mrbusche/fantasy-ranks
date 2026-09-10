import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fantasy_ranks.fetch_yahoo_draft import build_draft_results_url, fetch_yahoo_draft, main

SAMPLE_HTML = """
<html><body>
<div>Team Alpha</div>
<table>
<tr><td>1.</td><td>(1)</td><td>Josh Allen (Buf - QB)</td></tr>
<tr><td>4.</td><td>(4)</td><td>Amon-Ra St. Brown (Det - WR)</td></tr>
</table>
<div>Team Beta</div>
<table>
<tr><td>1.</td><td>(2)</td><td>Christian McCaffrey (SF - RB)</td></tr>
<tr><td>3.</td><td>(3)</td><td>Travis Kelce (KC - TE)</td></tr>
</table>
</body></html>
"""


def test_build_draft_results_url():
    assert build_draft_results_url('960067') == (
        'https://football.fantasysports.yahoo.com/f1/960067/draftresults?drafttab=team&draft_results_period=current'
    )


def test_fetch_yahoo_draft_requires_cookie(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('fantasy_ranks.yahoo_web.YAHOO_COOKIE', None)

    with pytest.raises(RuntimeError, match='YAHOO_COOKIE'):
        fetch_yahoo_draft('960067')


def test_fetch_yahoo_draft_saves_parsed_text(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('fantasy_ranks.yahoo_web.YAHOO_COOKIE', 'fake-cookie')
    monkeypatch.setattr('fantasy_ranks.fetch_yahoo_draft.ROSTERS_DIR', tmp_path / 'rosters')

    response = MagicMock()
    response.text = SAMPLE_HTML
    response.raise_for_status.return_value = None

    with patch('fantasy_ranks.yahoo_web.requests.get', return_value=response) as mock_get:
        output_path = fetch_yahoo_draft('960067')
        mock_get.assert_called_once()

    saved_text = open(output_path, encoding='utf-8').read()
    assert saved_text.splitlines() == [
        'Team Alpha',
        '1.\t(1)\tJosh Allen (Buf - QB)',
        '4.\t(4)\tAmon-Ra St. Brown (Det - WR)',
        'Team Beta',
        '1.\t(2)\tChristian McCaffrey (SF - RB)',
        '3.\t(3)\tTravis Kelce (KC - TE)',
    ]


def test_main_fetches_and_parses(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('fantasy_ranks.yahoo_web.YAHOO_COOKIE', 'fake-cookie')
    monkeypatch.setattr('fantasy_ranks.fetch_yahoo_draft.ROSTERS_DIR', tmp_path / 'rosters')
    monkeypatch.setattr('sys.argv', ['fetch_yahoo_draft', '960067'])

    response = MagicMock()
    response.text = SAMPLE_HTML
    response.raise_for_status.return_value = None

    output_file = tmp_path / 'rosters' / 'yahoo_960067_owned_players.json'
    assert not output_file.exists()

    with patch('fantasy_ranks.yahoo_web.requests.get', return_value=response):
        main()

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


def test_fetch_yahoo_draft_runs_when_owned_players_file_missing(tmp_path, monkeypatch):
    """fetch_yahoo_draft is the initial import step, so it must run even when no
    `yahoo_{league_id}_owned_players.json` file exists yet - unlike
    fetch_yahoo_transactions, which requires that file to already be present."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('fantasy_ranks.yahoo_web.YAHOO_COOKIE', 'fake-cookie')
    rosters_dir = tmp_path / 'rosters'
    monkeypatch.setattr('fantasy_ranks.fetch_yahoo_draft.ROSTERS_DIR', rosters_dir)

    owned_players_file = rosters_dir / 'yahoo_960067_owned_players.json'
    assert not owned_players_file.exists()

    response = MagicMock()
    response.text = SAMPLE_HTML
    response.raise_for_status.return_value = None

    with patch('fantasy_ranks.yahoo_web.requests.get', return_value=response) as mock_get:
        output_path = fetch_yahoo_draft('960067')
        mock_get.assert_called_once()

    assert (rosters_dir / 'yahoo_960067.txt') == Path(output_path)
    # fetch_yahoo_draft only downloads the raw text; parsing into owned_players.json is a separate step.
    assert not owned_players_file.exists()
