#!/usr/bin/env python3

import json
from collections import Counter
from pathlib import Path

import requests

VALID_PLATFORMS = ('espn', 'sleeper', 'yahoo')
VALID_SCORING_TYPES = ('half', 'full')
DEFAULT_SCORING_TYPE = 'half'

# Canonical starting-lineup slot categories used throughout the app.
DEFAULT_LINEUP_SLOTS = {'QB': 1, 'RB': 2, 'WR': 2, 'TE': 1, 'FLEX': 1, 'D/ST': 1, 'K': 1}

# Maps an ESPN roster slot label (from League.settings.position_slot_counts) to one of
# our canonical categories. Bench/IR/individual-defensive-player slots are intentionally
# left unmapped since this app only ranks offensive skill positions, D/ST, and K.
ESPN_SLOT_LABEL_MAP = {
    'QB': 'QB',
    'RB': 'RB',
    'WR': 'WR',
    'TE': 'TE',
    'RB/WR': 'FLEX',
    'WR/TE': 'FLEX',
    'RB/WR/TE': 'FLEX',
    'OP': 'SUPERFLEX',
    'D/ST': 'D/ST',
    'K': 'K',
}

# Maps a Sleeper roster_positions slot label to one of our canonical categories.
SLEEPER_SLOT_LABEL_MAP = {
    'QB': 'QB',
    'RB': 'RB',
    'WR': 'WR',
    'TE': 'TE',
    'FLEX': 'FLEX',
    'WRRB_FLEX': 'FLEX',
    'REC_FLEX': 'FLEX',
    'RB_WR_TE_FLEX': 'FLEX',
    'SUPER_FLEX': 'SUPERFLEX',
    'DEF': 'D/ST',
    'K': 'K',
}


NAME_REPLACEMENTS = {
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
    'tetairoa mcmillan': 'tet mcmillan',
    'zonovan knight': 'bam knight',
    'kenny gainwell': 'kenneth gainwell',
}


def _aggregate_lineup_slots(label_counts, label_map):
    """Aggregate a mapping of {slot_label: count} into our canonical lineup categories."""
    lineup_slots = {}
    for label, count in label_counts.items():
        category = label_map.get(label)
        if category:
            lineup_slots[category] = lineup_slots.get(category, 0) + count
    return lineup_slots


def validate_league(league):
    """Validate a single league config entry. Returns a list of error strings (empty if valid)."""
    errors = []

    platform = league.get('platform')
    if platform not in VALID_PLATFORMS:
        errors.append(f'platform must be one of {VALID_PLATFORMS}, got {platform!r}')

    league_id = league.get('league_id')
    if not (isinstance(league_id, (int, str)) and str(league_id).isdigit()):
        errors.append(f'league_id must be a number, got {league_id!r}')

    # scoring_type, league_name, and lineup_slots are optional - when omitted they are pulled from
    # the league's source system (see fetch_league_metadata) or defaulted.
    scoring_type = league.get('scoring_type')
    if scoring_type is not None and scoring_type not in VALID_SCORING_TYPES:
        errors.append(f'scoring_type must be one of {VALID_SCORING_TYPES}, got {scoring_type!r}')

    lineup_slots = league.get('lineup_slots')
    if lineup_slots is not None and not isinstance(lineup_slots, dict):
        errors.append(f'lineup_slots must be a dict of position -> starter count, got {lineup_slots!r}')

    team_name = league.get('team_name')
    if not isinstance(team_name, str) or not team_name.strip():
        errors.append('team_name is required')

    return errors


def _rec_points_to_scoring_type(rec_points):
    """Map a per-reception point value from a source system to our half/full scoring_type."""
    if rec_points is None:
        return None
    return 'full' if rec_points >= 1 else 'half'


def _fetch_espn_league_metadata(league_id):
    """Look up scoring_type, league_name, and lineup_slots from the ESPN API for a given league."""
    try:
        from espn_api.football import League

        from fantasy_ranks.espn_rosters import DEFAULT_YEAR, ESPN_S2, ESPN_SWID
    except ImportError:
        return {}

    try:
        league = League(league_id=int(league_id), year=DEFAULT_YEAR, swid=ESPN_SWID, espn_s2=ESPN_S2)
    except Exception:  # noqa: BLE001 - espn_api raises assorted custom exceptions we must swallow
        return {}

    metadata = {}
    league_name = getattr(league.settings, 'name', None)
    if league_name:
        metadata['league_name'] = league_name

    rec_points = next(
        (item.get('points') for item in getattr(league.settings, 'scoring_format', []) if item.get('abbr') == 'REC'),
        None,
    )
    scoring_type = _rec_points_to_scoring_type(rec_points)
    if scoring_type:
        metadata['scoring_type'] = scoring_type

    position_slot_counts = getattr(league.settings, 'position_slot_counts', None) or {}
    lineup_slots = _aggregate_lineup_slots(position_slot_counts, ESPN_SLOT_LABEL_MAP)
    if lineup_slots:
        metadata['lineup_slots'] = lineup_slots

    return metadata


def _fetch_sleeper_league_metadata(league_id):
    """Look up scoring_type, league_name, and lineup_slots from the Sleeper API for a given league."""
    try:
        resp = requests.get(f'https://api.sleeper.app/v1/league/{league_id}', timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return {}

    if not isinstance(data, dict):
        return {}

    metadata = {}
    league_name = data.get('name')
    if league_name:
        metadata['league_name'] = league_name

    rec_points = (data.get('scoring_settings') or {}).get('rec')
    scoring_type = _rec_points_to_scoring_type(rec_points)
    if scoring_type:
        metadata['scoring_type'] = scoring_type

    roster_positions = data.get('roster_positions') or []
    lineup_slots = _aggregate_lineup_slots(Counter(roster_positions), SLEEPER_SLOT_LABEL_MAP)
    if lineup_slots:
        metadata['lineup_slots'] = lineup_slots

    return metadata


def fetch_league_metadata(platform, league_id):
    """Fetch scoring_type/league_name/lineup_slots from a league's source system, when available.

    Returns a dict that may contain 'scoring_type', 'league_name', and/or 'lineup_slots' keys.
    'lineup_slots' is a dict like {'QB': 1, 'RB': 2, 'WR': 2, 'TE': 1, 'FLEX': 1, 'D/ST': 1, 'K': 1}
    describing the number of starting slots for each canonical position category, pulled from
    the league's actual roster settings so start/sit output reflects real lineup requirements.
    Network, auth, or parsing failures are swallowed - callers should fall back
    to config-provided values or defaults. Yahoo! rosters are maintained
    manually, so no source system lookup is available for that platform.
    """
    if platform == 'espn':
        return _fetch_espn_league_metadata(league_id)
    if platform == 'sleeper':
        return _fetch_sleeper_league_metadata(league_id)
    return {}


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
        # Pull missing scoring_type/league_name/lineup_slots from the source system before validating.
        if not league.get('scoring_type') or not league.get('league_name') or not league.get('lineup_slots'):
            metadata = fetch_league_metadata(league.get('platform'), league.get('league_id'))
            for key in ('scoring_type', 'league_name', 'lineup_slots'):
                if not league.get(key) and metadata.get(key):
                    league[key] = metadata[key]

        if not league.get('scoring_type'):
            league['scoring_type'] = DEFAULT_SCORING_TYPE

        if not league.get('lineup_slots'):
            league['lineup_slots'] = dict(DEFAULT_LINEUP_SLOTS)

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
    # Apply replacements
    for old, new in NAME_REPLACEMENTS.items():
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
