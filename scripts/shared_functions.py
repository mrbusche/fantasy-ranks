#!/usr/bin/env python3

import json
from pathlib import Path


VALID_PLATFORMS = ('espn', 'sleeper')
VALID_SCORING_TYPES = ('half', 'full')


def validate_league(league):
    """Validate a single league config entry. Returns a list of error strings (empty if valid)."""
    errors = []

    platform = league.get('platform')
    if platform not in VALID_PLATFORMS:
        errors.append(f'platform must be one of {VALID_PLATFORMS}, got {platform!r}')

    league_id = league.get('league_id')
    if not (isinstance(league_id, (int, str)) and str(league_id).isdigit()):
        errors.append(f'league_id must be a number, got {league_id!r}')

    scoring_type = league.get('scoring_type')
    if scoring_type not in VALID_SCORING_TYPES:
        errors.append(f'scoring_type must be one of {VALID_SCORING_TYPES}, got {scoring_type!r}')

    team_name = league.get('team_name')
    if not isinstance(team_name, str) or not team_name.strip():
        errors.append('team_name is required')

    return errors


def load_league_config(config_file=None):
    """Load league configuration from JSON file, validating each league entry."""
    if config_file is None:
        config_file = Path(__file__).parent.parent / 'config.json'

    try:
        with open(config_file, 'r', encoding='utf-8') as file:
            config = json.load(file)
    except FileNotFoundError:
        print(f'Error: Configuration file {config_file} not found.')
        return None
    except json.JSONDecodeError:
        print(f'Error: Invalid JSON in configuration file {config_file}.')
        return None

    leagues = config.get('leagues', []) if isinstance(config, dict) else []
    valid_leagues = []
    for league in leagues:
        errors = validate_league(league)
        if errors:
            name = league.get('team_name', league.get('league_name', 'Unknown'))
            print(f'⚠️  Skipping invalid league "{name}": {"; ".join(errors)}')
            continue
        valid_leagues.append(league)

    config['leagues'] = valid_leagues
    return config
