#!/usr/bin/env python3
"""
Generic fantasy football roster analysis script that works with ESPN, Yahoo, and Sleeper.
Analyzes a team's roster against weekly rankings and finds top available players.
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

from fantasy_ranks.shared_functions import (
    DEFAULT_LINEUP_SLOTS,
    get_all_owned_players,
    get_required_column,
    load_league_config,
    load_owned_players,
    names_match,
    normalize_name,
)

markdown_content = []

BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.resolve().parent.parent
RANKINGS_DIR = PROJECT_ROOT / 'rankings'
ROSTERS_DIR = PROJECT_ROOT / 'rosters'

PLAYER_NAME_COLUMN = 'Player Name'
POSITION_COLUMN = 'Position'
RANK_COLUMN = 'Rank'
TEAM_COLUMN = 'Team'


def load_custom_owned_players(file_path):
    """Load a custom list of owned players from a JSON file."""
    try:
        # Resolve path relative to script directory if it's not absolute
        path = Path(file_path)
        if not path.is_absolute():
            path = BASE_DIR / path

        with open(path, 'r', encoding='utf-8') as file:
            data = json.load(file)

            players = set()

            # Handle simple list of strings: ["Player 1", "Player 2"]
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, str):
                        players.add(item)
                        # Also add normalized version
                        normalized = normalize_name(item)
                        if normalized != item.lower().strip():
                            players.add(normalized)

            # Handle dict format (similar to owned_players.json or simple wrapper)
            elif isinstance(data, dict):
                # Check if it's a simple wrapper like {"owned": [...]}
                if 'owned' in data and isinstance(data['owned'], list):
                    for item in data['owned']:
                        if isinstance(item, str):
                            players.add(item)
                            players.add(normalize_name(item))

                # Or iterate through all values if they are lists (like team rosters)
                else:
                    for value in data.values():
                        if isinstance(value, list):
                            for item in value:
                                name = None
                                if isinstance(item, str):
                                    name = item
                                elif isinstance(item, dict) and 'name' in item:
                                    name = item['name']

                                if name:
                                    players.add(name)
                                    players.add(normalize_name(name))

            return players

    except FileNotFoundError:
        print(f'Warning: Custom owned file {file_path} not found.')
        return set()
    except json.JSONDecodeError:
        print(f'Error: Invalid JSON in custom owned file {file_path}.')
        return set()


def get_team_players(data, team_name):
    """Extract players for the specified team, handling different league types."""
    if not data:
        print('Error: No data provided')
        return None

    # For different league types, team names might be stored differently
    if team_name not in data:
        print(f"Error: Team '{team_name}' not found in data.")
        available_teams = list(data.keys()) if data else []
        print(f'Available teams: {available_teams}')
        return None

    return data[team_name]


def organize_by_position(players, league_type='espn'):
    """Organize players by their position, handling different league formats."""
    players_by_position = defaultdict(list)

    for player in players:
        # Handle different position field names based on league type
        position = player.get('position', 'Unknown')

        # Handle different team field names based on league type
        if league_type == 'sleeper':
            team = player.get('nfl_team', 'Unknown')
        else:
            team = player.get('proTeam', 'Unknown')

        player_info = {
            'name': player.get('name', 'Unknown'),
            'proTeam': team,
            'injured': player.get('injured', False),
            'totalPoints': player.get('totalPoints', 0.0),
        }

        players_by_position[position].append(player_info)

    return players_by_position


def load_rankings(scoring_type='half'):
    """Load ranking CSV files based on scoring type (half or ppr)."""
    rankings = {}

    # Choose flex file based on scoring type
    flex_file = 'half_flex.csv' if scoring_type == 'half' else 'ppr_flex.csv'

    # Mapping of CSV files to positions
    ranking_files = {
        'qb.csv': 'QB',
        flex_file: ['RB', 'WR', 'TE'],  # Flex positions
        'dst.csv': 'D/ST',
        'kicker.csv': 'K',
    }

    for filename, positions in ranking_files.items():
        file_path = RANKINGS_DIR / filename
        if not file_path.exists():
            print(f'Warning: {filename} not found in rankings directory')
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                # Initialize position dictionaries
                if isinstance(positions, list):
                    for pos in positions:
                        if pos not in rankings:
                            rankings[pos] = {}
                else:
                    rankings[positions] = {}

                for row in reader:
                    player_name = get_required_column(row, PLAYER_NAME_COLUMN, 'PLAYER_NAME_COLUMN', filename).strip()
                    rank = int(get_required_column(row, RANK_COLUMN, 'RANK_COLUMN', filename) or 0)
                    team = get_required_column(row, TEAM_COLUMN, 'TEAM_COLUMN', filename).strip()
                    position = get_required_column(row, POSITION_COLUMN, 'POSITION_COLUMN', filename).strip()

                    # Handle D/ST naming convention
                    if position == 'DST':
                        position = 'D/ST'
                        if not player_name.endswith(' D/ST'):
                            player_name = f'{player_name} D/ST'

                        # Normalize D/ST names to use short team names
                        normalized_name = normalize_name(player_name)
                        if normalized_name != player_name.lower().strip():
                            player_name = f'{normalized_name.title()} D/ST'

                    # Store ranking info
                    ranking_info = {
                        'rank': rank,
                        'team': team,
                        'position': position,
                        'player_name': player_name,
                    }

                    # Add to appropriate position category
                    if isinstance(positions, list):
                        if position in positions:
                            rankings[position][player_name] = ranking_info
                    else:
                        rankings[positions][player_name] = ranking_info

        except (OSError, FileNotFoundError, KeyError, ValueError) as e:
            print(f'Error loading {filename}: {e}')

    return rankings


def find_player_ranking(player_name, position, rankings):
    """Find a player's ranking in the appropriate CSV file."""
    if position not in rankings:
        return None

    # Direct name match
    if player_name in rankings[position]:
        return rankings[position][player_name]

    # Handle D/ST special cases
    if position == 'D/ST':
        variations = [
            player_name,
            player_name.replace(' D/ST', ''),
            f'{player_name.split()[0]} D/ST' if ' ' in player_name else player_name,
        ]

        for variation in variations:
            if variation in rankings[position]:
                return rankings[position][variation]

        # Try matching team abbreviations for D/ST
        for ranked_name in rankings[position]:
            ranked_team = rankings[position][ranked_name]['team']
            if player_name.startswith(ranked_team) or ranked_team in player_name:
                return rankings[position][ranked_name]

    # Try partial matching for other positions
    for ranked_name in rankings[position]:
        if names_match(player_name, ranked_name):
            return rankings[position][ranked_name]

    return None


def get_available_players_by_position(rankings, all_owned_players):
    """Get available (unowned) players by position from rankings data."""
    available_by_position = defaultdict(list)
    normalized_owned_players = {normalize_name(name) for name in all_owned_players}

    for position, position_rankings in rankings.items():
        for player_name, ranking_info in position_rankings.items():
            # Create a more comprehensive ownership check
            is_owned = False

            # Direct name check
            if player_name in all_owned_players:
                is_owned = True
            else:
                # Normalize the ranking player name
                normalized_ranking_name = normalize_name(player_name)

                if normalized_ranking_name in normalized_owned_players:
                    continue

                # Compare with pre-normalized names to avoid repeating work.
                for normalized_owned_name in normalized_owned_players:
                    # Check various matching scenarios
                    if (
                        normalized_ranking_name == normalized_owned_name
                        or normalized_ranking_name in normalized_owned_name
                        or normalized_owned_name in normalized_ranking_name
                        or (position == 'D/ST' and normalized_ranking_name in normalized_owned_name)
                        or (position == 'D/ST' and normalized_owned_name in normalized_ranking_name)
                    ):
                        is_owned = True
                        break

            if not is_owned:
                available_by_position[position].append(
                    {
                        'name': player_name,
                        'proTeam': ranking_info['team'],
                        'injured': False,  # No injury data in rankings
                        'rank': ranking_info['rank'],
                        'position': ranking_info['position'],
                    }
                )

    return available_by_position


def safe_print(text):
    """Add text to Markdown content instead of printing"""
    markdown_content.append(text)


TOP_N_AVAILABLE = 5
BASE_SLOT_POSITIONS = ['QB', 'RB', 'WR', 'TE', 'K', 'D/ST']
FLEX_ELIGIBLE_POSITIONS = ['RB', 'WR', 'TE']
SUPERFLEX_ELIGIBLE_POSITIONS = ['QB', 'RB', 'WR', 'TE']
TOP_LIST_SECTIONS = [
    ('QB', 'Quarterbacks (QB)'),
    ('RB', 'Running Backs (RB)'),
    ('WR', 'Wide Receivers (WR)'),
    ('TE', 'Tight Ends (TE)'),
    ('FLEX', 'Flex (RB/WR/TE)'),
    ('D/ST', 'Defense (D/ST)'),
    ('K', 'Kickers (K)'),
]


def _position_label(position):
    """Short display label for a position (D/ST displays as DST to match FA name formatting)."""
    return 'DST' if position == 'D/ST' else position


def _format_rank(position, ordinal):
    """Format a position-specific ordinal rank for display, e.g. 'RB5', 'QB26'."""
    return f'{_position_label(position)}{ordinal}'


def _compute_position_ordinal_ranks(rankings, position):
    """Compute a 1-based ordinal rank per player within a single position.

    RB/WR/TE share a combined flex ranking file, so their raw 'rank' values are ranked
    across all three positions together rather than purely within one position. This
    recomputes a position-only ordinal (e.g. 'RB5') so the starting roster table shows
    ranks relative to other players at the same position, which is what a start/sit
    decision actually needs.
    """
    entries = sorted(rankings.get(position, {}).values(), key=lambda info: info['rank'])
    return {info['player_name']: idx + 1 for idx, info in enumerate(entries)}


def _evaluate_slot(starter_value, fa_value):
    """Compare a starter's rank against the best available free agent's rank.

    Returns 'Unranked' if the starter has no ranking, 'No Free Agents Available' if there
    is no free agent to compare against, 'Optimal' if the starter is already the better
    option, or '+N Ranks Better' showing how much stronger the free agent's rank is.
    """
    if starter_value is None:
        return 'Unranked'
    if fa_value is None:
        return 'No Free Agents Available'
    if starter_value <= fa_value:
        return 'Optimal'
    return f'+{starter_value - fa_value} Ranks Better'


def _print_starting_roster_table(players_by_position, available_by_position, rankings, lineup_slots):
    """Print one row per starting lineup slot, comparing each starter to the single best
    available free agent at that position/FLEX/SUPERFLEX so the recommendation is
    concrete and actionable rather than a generic list of top players.

    A slot configured with 0 starters still gets a single informational row so the
    league's actual lineup shape (including positions it doesn't use) stays visible.

    Returns the set of (position, player_name) keys used as starters so callers can
    determine which rostered players are on the bench.
    """
    ordinal_ranks = {position: _compute_position_ordinal_ranks(rankings, position) for position in BASE_SLOT_POSITIONS}

    safe_print('| Slot | Starter | Current Rank | Best Available Free Agent | FA Rank | Evaluation |')
    safe_print('|------|---------|--------------|---------------------------|---------|------------|')

    flex_candidates = []  # Leftover RB/WR/TE team players not needed for their own position's slots
    superflex_pool = []  # Leftover QB players, plus FLEX-eligible players not used by FLEX slots
    starter_keys = set()

    for position in BASE_SLOT_POSITIONS:
        starters_needed = lineup_slots.get(position, DEFAULT_LINEUP_SLOTS.get(position, 1))

        ordinal_map = ordinal_ranks[position]

        team_entries = []
        for player in players_by_position.get(position, []):
            ranking_info = find_player_ranking(player['name'], position, rankings)
            team_entries.append(
                {
                    'name': player['name'],
                    'position': position,
                    'ranking_info': ranking_info,
                    'rank': ranking_info['rank'] if ranking_info else float('inf'),
                }
            )
        team_entries.sort(key=lambda e: e['rank'])

        leftover_entries = team_entries[max(starters_needed, 0) :]
        if position in FLEX_ELIGIBLE_POSITIONS:
            flex_candidates.extend(leftover_entries)
        elif position == 'QB':
            superflex_pool.extend(leftover_entries)

        if starters_needed <= 0:
            _print_zero_starter_row(position)
            continue

        available_entries = sorted(available_by_position.get(position, []), key=lambda p: p['rank'])
        best_fa = available_entries[0] if available_entries else None
        fa_ordinal = ordinal_map.get(best_fa['name']) if best_fa else None

        for idx in range(starters_needed):
            entry = team_entries[idx] if idx < len(team_entries) else None
            _print_slot_row(position, entry, ordinal_map, best_fa, fa_ordinal)
            if entry is not None:
                starter_keys.add((position, entry['name']))

    flex_slots = lineup_slots.get('FLEX', DEFAULT_LINEUP_SLOTS.get('FLEX', 0))
    flex_candidates.sort(key=lambda e: e['rank'])

    if flex_slots > 0:
        flex_available = []
        for position in FLEX_ELIGIBLE_POSITIONS:
            flex_available.extend(available_by_position.get(position, []))
        flex_available.sort(key=lambda p: p['rank'])
        best_flex_fa = flex_available[0] if flex_available else None

        for idx in range(flex_slots):
            entry = flex_candidates[idx] if idx < len(flex_candidates) else None
            _print_pooled_slot_row('FLEX', entry, best_flex_fa, ordinal_ranks)
            if entry is not None:
                starter_keys.add((entry['position'], entry['name']))

    # Leftover FLEX-eligible players beyond FLEX allocation are also SUPERFLEX-eligible.
    superflex_pool.extend(flex_candidates[max(flex_slots, 0) :])

    superflex_slots = lineup_slots.get('SUPERFLEX', DEFAULT_LINEUP_SLOTS.get('SUPERFLEX', 0))
    if superflex_slots > 0:
        superflex_pool.sort(key=lambda e: e['rank'])

        superflex_available = []
        for position in SUPERFLEX_ELIGIBLE_POSITIONS:
            superflex_available.extend(available_by_position.get(position, []))
        superflex_available.sort(key=lambda p: p['rank'])
        best_superflex_fa = superflex_available[0] if superflex_available else None

        for idx in range(superflex_slots):
            entry = superflex_pool[idx] if idx < len(superflex_pool) else None
            _print_pooled_slot_row('SUPERFLEX', entry, best_superflex_fa, ordinal_ranks)
            if entry is not None:
                starter_keys.add((entry['position'], entry['name']))

    return starter_keys


def _print_zero_starter_row(slot_label):
    """Print a single informational row for a slot the league doesn't start (0 configured
    starters), so the report still reflects the league's full lineup shape. Unused kicker
    and defense slots are omitted because they do not provide actionable recommendations.
    """
    if slot_label in ('K', 'D/ST'):
        return
    safe_print(f'| {slot_label} | — (0 Starters Configured) | — | — | — | Not Started |')


def _evaluate_empty_slot(best_fa):
    """Evaluation message for a starting slot with no rostered player at all."""
    return 'Fill via Free Agent' if best_fa else 'No Player Rostered'


def _print_slot_row(position, entry, ordinal_map, best_fa, fa_ordinal):
    """Print a single starting-lineup row for a non-FLEX position."""
    position_label = _position_label(position)

    if entry is None:
        starter_cell = '— (Empty Slot)'
        current_rank_cell = '—'
        evaluation = _evaluate_empty_slot(best_fa)
    else:
        starter_cell = f'{entry["name"]} ({position_label})'
        ranking_info = entry['ranking_info']
        starter_ordinal = ordinal_map.get(ranking_info['player_name']) if ranking_info else None
        current_rank_cell = _format_rank(position, starter_ordinal) if starter_ordinal else '—'
        evaluation = _evaluate_slot(starter_ordinal, fa_ordinal)

    if best_fa:
        fa_cell = f'{best_fa["name"]} ({position_label} - {best_fa["proTeam"]})'
        fa_rank_cell = _format_rank(position, fa_ordinal) if fa_ordinal else '—'
    else:
        fa_cell = '—'
        fa_rank_cell = '—'

    safe_print(f'| {position} | {starter_cell} | {current_rank_cell} | {fa_cell} | {fa_rank_cell} | {evaluation} |')


def _format_pooled_rank(slot_label, ranking_info, ordinal_ranks):
    """Format a pooled-slot rank with the player's specific position rank."""
    if not ranking_info:
        return '—'

    position = ranking_info['position']
    player_name = ranking_info.get('player_name', ranking_info.get('name'))
    ordinal = ordinal_ranks.get(position, {}).get(player_name)
    position_rank = _format_rank(position, ordinal) if ordinal else None
    if slot_label == 'FLEX':
        flex_rank = f'FLEX#{ranking_info["rank"]}'
        return f'{position_rank} / {flex_rank}' if position_rank else flex_rank
    return f'#{ranking_info["rank"]}'


def _print_pooled_slot_row(slot_label, entry, best_fa, ordinal_ranks):
    """Print a single starting-lineup row for a pooled multi-position slot (FLEX or SUPERFLEX).

    FLEX slots show both each player's position-specific rank and combined FLEX rank.
    SUPERFLEX slots continue to show the raw combined rank as '#N'.
    """
    if entry is None:
        starter_cell = '— (Empty Slot)'
        current_rank_cell = '—'
        evaluation = _evaluate_empty_slot(best_fa)
    else:
        ranking_info = entry['ranking_info']
        starter_position = ranking_info['position'] if ranking_info else None
        pos_suffix = f' ({starter_position})' if starter_position else ''
        starter_cell = f'{entry["name"]}{pos_suffix}'
        starter_rank = ranking_info['rank'] if ranking_info else None
        current_rank_cell = _format_pooled_rank(slot_label, ranking_info, ordinal_ranks)
        fa_rank = best_fa['rank'] if best_fa else None
        evaluation = _evaluate_slot(starter_rank, fa_rank)

    if best_fa:
        fa_position_label = _position_label(best_fa['position'])
        fa_cell = f'{best_fa["name"]} ({fa_position_label} - {best_fa["proTeam"]})'
        fa_rank_cell = _format_pooled_rank(slot_label, best_fa, ordinal_ranks)
    else:
        fa_cell = '—'
        fa_rank_cell = '—'

    safe_print(f'| {slot_label} | {starter_cell} | {current_rank_cell} | {fa_cell} | {fa_rank_cell} | {evaluation} |')


def _print_bench_table(players_by_position, rankings, starter_keys):
    """Print the team's remaining rostered players (those not in a starting slot) along
    with their current rank, so bench depth is visible alongside the starting lineup.
    """
    ordinal_ranks = {position: _compute_position_ordinal_ranks(rankings, position) for position in BASE_SLOT_POSITIONS}

    safe_print('### Bench')
    safe_print('')

    rows = []
    for position in BASE_SLOT_POSITIONS:
        ordinal_map = ordinal_ranks[position]
        for player in players_by_position.get(position, []):
            if (position, player['name']) in starter_keys:
                continue

            ranking_info = find_player_ranking(player['name'], position, rankings)
            ordinal = ordinal_map.get(player['name']) if ranking_info else None
            if ranking_info and position in FLEX_ELIGIBLE_POSITIONS:
                rank_label = _format_pooled_rank('FLEX', ranking_info, ordinal_ranks)
                sort_rank = ranking_info['rank']
            else:
                rank_label = _format_rank(position, ordinal) if ordinal else 'Unranked'
                sort_rank = ordinal if ordinal is not None else float('inf')
            rows.append((sort_rank, f'{player["name"]} ({_position_label(position)})', rank_label))

    if not rows:
        safe_print('No bench players found.')
        safe_print('')
        return

    rows.sort(key=lambda r: r[0])

    safe_print('| Player | Current Rank |')
    safe_print('|--------|---------------|')
    for _, player_cell, rank_cell in rows:
        safe_print(f'| {player_cell} | {rank_cell} |')

    safe_print('')


def _print_top_available_lists(available_by_position, rankings, lineup_slots):
    """Print the top N available free agents for each position, plus a combined FLEX list
    and (only when the league uses one) a combined SUPERFLEX list.
    """
    ordinal_ranks = {position: _compute_position_ordinal_ranks(rankings, position) for position in BASE_SLOT_POSITIONS}

    sections = list(TOP_LIST_SECTIONS)
    if lineup_slots.get('SUPERFLEX', DEFAULT_LINEUP_SLOTS.get('SUPERFLEX', 0)) > 0:
        sections.append(('SUPERFLEX', 'Superflex (QB/RB/WR/TE)'))

    safe_print(f'### Top {TOP_N_AVAILABLE} Available Players by Position')
    safe_print('')

    for position, label in sections:
        safe_print(f'#### {label}')
        safe_print('')

        if position in ('FLEX', 'SUPERFLEX'):
            eligible_positions = FLEX_ELIGIBLE_POSITIONS if position == 'FLEX' else SUPERFLEX_ELIGIBLE_POSITIONS
            entries = []
            for pool_position in eligible_positions:
                entries.extend(available_by_position.get(pool_position, []))
            entries.sort(key=lambda p: p['rank'])
            top_entries = entries[:TOP_N_AVAILABLE]
            rows = []
            for p in top_entries:
                rank_info = {
                    'position': p['position'],
                    'player_name': p['name'],
                    'rank': p['rank'],
                }
                rank_label = _format_pooled_rank(position, rank_info, ordinal_ranks)
                rows.append((f'{p["name"]} ({_position_label(p["position"])} - {p["proTeam"]})', rank_label))
        else:
            entries = sorted(available_by_position.get(position, []), key=lambda p: p['rank'])
            top_entries = entries[:TOP_N_AVAILABLE]
            ordinal_map = ordinal_ranks[position]
            rows = []
            for p in top_entries:
                ordinal = ordinal_map.get(p['name'])
                rank_label = _format_rank(position, ordinal) if ordinal else '—'
                rows.append((f'{p["name"]} ({_position_label(position)} - {p["proTeam"]})', rank_label))

        if not rows:
            safe_print('No available players found.')
        else:
            safe_print('| Player | Rank |')
            safe_print('|--------|------|')
            for name_cell, rank_cell in rows:
                safe_print(f'| {name_cell} | {rank_cell} |')

        safe_print('')


def print_combined_position_rankings(
    players_by_position, all_owned_players, rankings, team_name, league_name, lineup_slots=None
):
    """Print the team's concrete starting lineup recommendation and the top available
    free agents by position.

    The starting roster table lists one row per starting slot (based on the league's
    actual lineup_slots), each compared against the single best available free agent at
    that slot with an explicit evaluation ('Optimal' or '+N Ranks Better'). A Bench
    section then lists remaining rostered players and their current rank, followed by a
    section listing the top available free agents by position (including a combined
    FLEX view) for a broader picture of the waiver wire.
    """
    lineup_slots = lineup_slots or DEFAULT_LINEUP_SLOTS

    safe_print(f'### {league_name} {team_name} — Starting Roster')
    safe_print('')

    available_by_position = get_available_players_by_position(rankings, all_owned_players)

    starter_keys = _print_starting_roster_table(players_by_position, available_by_position, rankings, lineup_slots)
    safe_print('')

    _print_bench_table(players_by_position, rankings, starter_keys)

    _print_top_available_lists(available_by_position, rankings, lineup_slots)


def output_rankings(
    team_name,
    scoring_type='half',
    league_type='espn',
    file_prefix: str | None = None,
    league_name=None,
    custom_owned_path=None,
    rankings=None,
    lineup_slots=None,
):
    """
    Main function to analyze a team's roster against weekly rankings.

    Args:
        team_name (str): Name of the team to analyze
        scoring_type (str): Scoring system - "half" or "ppr" (default: "half")
        league_type (str): League platform - "espn", "yahoo", or "sleeper" (default: "espn")
        file_prefix (str): Optional prefix for the league files (e.g., "LeagueOfDreams")
        league_name (str): Name of the league for display
        custom_owned_path (str): Optional path to a custom JSON file with owned players
        rankings (dict): Optional pre-loaded player rankings to use for analysis
        lineup_slots (dict): Starting lineup slot counts pulled from the league's source system
            (e.g. {'QB': 1, 'RB': 2, 'WR': 2, 'TE': 1, 'FLEX': 1, 'D/ST': 1, 'K': 1}). Falls back
            to DEFAULT_LINEUP_SLOTS when not provided.

    Returns:
        bool: True if analysis completed successfully, False otherwise
    """

    safe_print(f'## 🏈 Analyzing team: {team_name}')
    safe_print('')
    if league_type:
        safe_print(f'- **League type:** {league_type.upper()}')
    if file_prefix:
        safe_print(f'- **League:** {file_prefix}')
    safe_print(f'- **Scoring:** {scoring_type.upper()}')

    owned_players_data = {}
    team_players = []

    if league_type:
        json_file = ROSTERS_DIR / f'{file_prefix}_owned_players.json'
        safe_print(f'- **Data file:** {json_file}')

        # Load the data
        owned_players_data = load_owned_players(json_file)
        if not owned_players_data:
            if league_type == 'yahoo' and not json_file.exists() and file_prefix:
                league_id = file_prefix.replace('yahoo_', '')
                print(
                    f'💡 Reminder: Yahoo! rosters are imported manually. Save the draft results to '
                    f'rosters\\{file_prefix}.txt, then run: '
                    f'uv run python src\\fantasy_ranks\\parse_yahoo_draft.py {league_id}'
                )
            return False

        # Get the team's players
        team_players = get_team_players(owned_players_data, team_name)
        if not team_players:
            return False

    safe_print('')

    # Organize by position
    players_by_position = organize_by_position(team_players, league_type)

    # Get all owned players across all teams
    all_owned_players = get_all_owned_players(owned_players_data)

    # Load custom owned players if specified
    if custom_owned_path:
        safe_print(f'- **Custom owned file:** {custom_owned_path}')
        custom_owned = load_custom_owned_players(custom_owned_path)
        if custom_owned:
            count_before = len(all_owned_players)
            all_owned_players.update(custom_owned)
            safe_print(f'  - Added {len(all_owned_players) - count_before} players from custom list')

    if rankings is None:
        rankings = load_rankings(scoring_type)

    if not rankings:
        safe_print('**No rankings found!**')
        return False

    # Show combined rankings (team's players marked Start/Bench + available by position)
    print_combined_position_rankings(
        players_by_position, all_owned_players, rankings, team_name, league_name, lineup_slots
    )

    return True


def save_markdown():
    """Save the Markdown content to start-sit.md"""
    output_file = Path(__file__).resolve().parent.parent.parent / 'lineups' / 'start-sit.md'
    output_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(markdown_content))
        print(f'✅ Successfully saved analysis to {output_file}')
    except (OSError, TypeError) as e:
        print(f'❌ Error saving to {output_file}: {e}')


def main():
    """Load league configuration and analyze all configured leagues."""
    global markdown_content
    markdown_content = []  # Reset content

    safe_print('# Fantasy Football Start/Sit Analysis')
    safe_print('')

    # Load league configuration
    config = load_league_config()
    if not config or 'leagues' not in config:
        print('❌ Failed to load league configuration or no leagues found.')
        return

    leagues = config['leagues']
    if not leagues:
        print('❌ No leagues configured.')
        return

    print(f'📋 Found {len(leagues)} leagues in configuration')

    rankings_by_scoring_type = {}

    # Process each league
    for i, league in enumerate(leagues, 1):
        print(f'🔄 Processing league {i}/{len(leagues)}: {league.get("team_name", "Unknown")}')

        # Validate required fields
        required_fields = ['team_name', 'scoring_type', 'league_id', 'platform']
        missing_fields = [field for field in required_fields if field not in league]

        if missing_fields:
            print(f'⚠️  Skipping league "{league.get("team_name", "Unknown")}" - missing fields: {missing_fields}')
            continue

        # Add separator between leagues
        if i > 1:
            safe_print('\n---\n')

        scoring_type = league['scoring_type']
        if scoring_type not in rankings_by_scoring_type:
            rankings_by_scoring_type[scoring_type] = load_rankings(scoring_type)

        # Run analysis for this league
        success = output_rankings(
            team_name=league['team_name'],
            scoring_type=scoring_type,
            league_type=league['platform'],
            file_prefix=f'{league["platform"]}_{league["league_id"]}',
            league_name=league.get('league_name', ''),
            custom_owned_path=league.get('custom_owned_file'),
            rankings=rankings_by_scoring_type[scoring_type],
            lineup_slots=league.get('lineup_slots'),
        )

        if success:
            print(f'✅ Completed analysis for {league["team_name"]}')
        else:
            print(f'❌ Failed to analyze {league["team_name"]}')

    # Save the markdown content
    save_markdown()


if __name__ == '__main__':
    main()
