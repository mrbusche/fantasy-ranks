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
        config_file = Path(__file__).parent.parent.parent / 'config.json'

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


def get_required_column(row, column_name, column_var_name, filename):
    """Get a required column's value from a CSV row, raising a helpful error if missing."""
    value = row.get(column_name)
    if value is None:
        raise ValueError(
            f"Column '{column_name}' not found in {filename}. "
            f'Available columns: {list(row.keys())}. '
            f'Update {column_var_name} at the top of output_rankings.py to match your CSV headers.'
        )
    return value


def names_match(name1, name2):
    """Check if two player names likely refer to the same player."""
    # Normalize names first
    name1_normalized = normalize_name(name1)
    name2_normalized = normalize_name(name2)

    # Exact match after normalization
    if name1_normalized == name2_normalized:
        return True

    # Check if one name contains the other
    return bool(name1_normalized in name2_normalized or name2_normalized in name1_normalized)


def normalize_name(name):
    """Normalize player names to handle common variations."""
    if not name:
        return ''

    # Convert to lowercase for comparison
    normalized = name.lower().strip()

    # Common name replacements for regular players
    replacements = {
        # Suffix variations
        ' jr.': '',
        ' jr': '',
        ' sr.': '',
        ' sr': '',
        ' iii': '',
        ' ii': '',
        ' iv': '',
        ' v': '',
        "'": '',
        '-': '',
        '.': '',
        # Specific player name variations
        'tetairoa mcmillan': 'tet mcmillan',
        'zonovan knight': 'bam knight',
        'kenny gainwell': 'kenneth gainwell',
    }

    # Apply replacements
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)

    return normalized.strip()


def get_all_owned_players(data):
    """Get all owned players across all teams."""
    all_owned = set()
    for team_players in data.values():
        for player in team_players:
            # Store both original and normalized names
            player_name = player.get('name', '').strip()
            all_owned.add(player_name)
            # Also add normalized version for better matching
            normalized = normalize_name(player_name)
            if normalized != player_name.lower().strip():
                all_owned.add(normalized)
    return all_owned


def load_owned_players(file_path):
    """Load the owned players data from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f'Error: File {file_path} not found.')
        return None
    except json.JSONDecodeError:
        print(f'Error: Invalid JSON in file {file_path}.')
        return None
