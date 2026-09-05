"""Shared pytest fixtures for the fantasy_ranks test suite.

These fixtures provide reusable factories for mocking the external ESPN and
Sleeper HTTP APIs so individual tests don't need to hand-roll response mocks.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_espn_league():
    """Factory fixture that builds a fake `espn_api.football.League` object.

    Usage:
        league = mock_espn_league([
            {
                "team_name": "Chiefs Kingdom",
                "players": [
                    {"name": "Patrick Mahomes", "position": "QB", "proTeam": "KC"},
                ],
            }
        ])
    """

    def _build(teams_data):
        teams = []
        for team in teams_data:
            roster = [
                SimpleNamespace(
                    name=player['name'],
                    position=player.get('position', 'QB'),
                    proTeam=player.get('proTeam', 'FA'),
                    injured=player.get('injured', False),
                    total_points=player.get('total_points', 0.0),
                )
                for player in team.get('players', [])
            ]
            teams.append(SimpleNamespace(team_name=team['team_name'], roster=roster))
        return SimpleNamespace(teams=teams)

    return _build


@pytest.fixture
def mock_requests_response():
    """Factory fixture that builds a MagicMock resembling a `requests` JSON response.

    Usage:
        response = mock_requests_response({"key": "value"})
        with patch('requests.get', return_value=response):
            ...
    """

    def _build(json_data, raise_error=None):
        response = MagicMock()
        response.json.return_value = json_data
        if raise_error is not None:
            response.raise_for_status.side_effect = raise_error
        else:
            response.raise_for_status.return_value = None
        return response

    return _build


@pytest.fixture
def sleeper_player_db():
    """A small sample Sleeper master player database keyed by player id."""
    return {
        'p1': {
            'first_name': 'Justin',
            'last_name': 'Jefferson',
            'position': 'WR',
            'team': 'MIN',
            'search_rank': 1,
        },
        'DEF_SF': {
            'first_name': 'San Francisco',
            'last_name': '49ers',
            'position': 'DEF',
            'team': None,
            'search_rank': None,
        },
    }
