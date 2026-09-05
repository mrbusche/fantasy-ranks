#!/usr/bin/env python3
"""
Generic fantasy football roster analysis script that works with ESPN, Yahoo, and Sleeper.
Analyzes a team's roster against weekly rankings and finds top available players.
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

from shared_functions import load_league_config

# Global variable to store markdown content
markdown_content = []

# Set UTF-8 encoding for stdout to handle Unicode characters
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).parent
RANKINGS_DIR = BASE_DIR.parent / 'rankings'
ROSTERS_DIR = BASE_DIR.parent / 'rosters'


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


def load_custom_owned_players(file_path):
    """Load a custom list of owned players from a JSON file."""
    try:
        # Resolve path relative to script directory if it's not absolute
        path = Path(file_path)
        if not path.is_absolute():
            BASE_DIR = Path(__file__).parent
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
                        normalized = _normalize_name(item)
                        if normalized != item.lower().strip():
                            players.add(normalized)

            # Handle dict format (similar to owned_players.json or simple wrapper)
            elif isinstance(data, dict):
                # Check if it's a simple wrapper like {"owned": [...]}
                if 'owned' in data and isinstance(data['owned'], list):
                    for item in data['owned']:
                        if isinstance(item, str):
                            players.add(item)
                            players.add(_normalize_name(item))

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
                                    players.add(_normalize_name(name))

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


def get_all_owned_players(data):
    """Get all owned players across all teams."""
    all_owned = set()
    for team_players in data.values():
        for player in team_players:
            # Store both original and normalized names
            player_name = player.get('name', '').strip()
            all_owned.add(player_name)
            # Also add normalized version for better matching
            normalized = _normalize_name(player_name)
            if normalized != player_name.lower().strip():
                all_owned.add(normalized)
    return all_owned


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
                    player_name = row.get('Player Name', '').strip()
                    rank = int(row.get('Rank', 0))
                    team = row.get('Team', '').strip()
                    position = row.get('Position', '').strip()

                    # Handle D/ST naming convention
                    if position == 'DST':
                        position = 'D/ST'
                        if not player_name.endswith(' D/ST'):
                            player_name = f'{player_name} D/ST'

                        # Normalize D/ST names to use short team names
                        normalized_name = _normalize_name(player_name)
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
        if _names_match(player_name, ranked_name):
            return rankings[position][ranked_name]

    return None


def _names_match(name1, name2):
    """Check if two player names likely refer to the same player."""
    # Normalize names first
    name1_normalized = _normalize_name(name1)
    name2_normalized = _normalize_name(name2)

    # Exact match after normalization
    if name1_normalized == name2_normalized:
        return True

    # Check if one name contains the other
    return bool(name1_normalized in name2_normalized or name2_normalized in name1_normalized)


def _normalize_name(name):
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


def _print_position_players(position, players):
    """Helper function to print players for a specific position."""
    print(f'\n{position}:')
    print('-' * 30)

    sorted_players = sorted(players, key=lambda x: x['totalPoints'], reverse=True)

    for i, player in enumerate(sorted_players, 1):
        injury_status = ' (INJURED)' if player['injured'] else ''
        print(
            f'{i:2d}. {player["name"]:<25} | {player["proTeam"]:<3} | {player["totalPoints"]:>6.1f} pts{injury_status}'
        )


def get_available_players_by_position(rankings, all_owned_players):
    """Get available (unowned) players by position from rankings data."""
    available_by_position = defaultdict(list)

    for position, position_rankings in rankings.items():
        for player_name, ranking_info in position_rankings.items():
            # Create a more comprehensive ownership check
            is_owned = False

            # Direct name check
            if player_name in all_owned_players:
                is_owned = True
            else:
                # Normalize the ranking player name
                normalized_ranking_name = _normalize_name(player_name)

                # Check against all owned players (both original and normalized)
                for owned_name in all_owned_players:
                    normalized_owned_name = _normalize_name(owned_name)

                    # Check various matching scenarios
                    if (
                        normalized_ranking_name == normalized_owned_name
                        or _names_match(player_name, owned_name)
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
    """Add text to markdown content instead of printing"""
    markdown_content.append(text)


def print_combined_position_rankings(players_by_position, all_owned_players, rankings, team_name, league_name):
    """Print team's players combined with top 5 available for each position."""
    safe_print(f'## COMBINED RANKINGS: {league_name.upper()} {team_name.upper()} + TOP 5 AVAILABLE BY POSITION')
    safe_print('')

    # Get available players from rankings
    available_by_position = get_available_players_by_position(rankings, all_owned_players)

    for position in ['QB', 'RB', 'WR', 'TE', 'Flex', 'K', 'D/ST']:
        if position == 'Flex':
            # Handle Flex position (combine RB, WR, and TE)
            team_players = []

            # Combine team players from RB, WR, and TE
            for flex_pos in ['RB', 'WR', 'TE']:
                if flex_pos in players_by_position:
                    for player in players_by_position[flex_pos]:
                        ranking_info = find_player_ranking(player['name'], flex_pos, rankings)
                        if ranking_info:
                            team_players.append(
                                {
                                    'name': player['name'],
                                    'team': player['proTeam'],
                                    'rank': ranking_info['rank'],
                                    'owned_by': 'Team',
                                    'position': flex_pos,  # Keep original position for display
                                }
                            )

            # Combine available players from RB, WR, and TE
            available_players = []
            for flex_pos in ['RB', 'WR', 'TE']:
                flex_available = available_by_position.get(flex_pos, [])
                for player in flex_available:
                    available_players.append(
                        {
                            'name': player['name'],
                            'proTeam': player['proTeam'],
                            'rank': player['rank'],
                            'owned_by': 'Available',
                            'position': flex_pos,
                        }
                    )

            # Sort available players and take top 10 for Flex (more options needed)
            available_players.sort(key=lambda x: x['rank'])
            top_available = available_players[:10]

            # Add ownership info and team consistency
            for player in top_available:
                player['team'] = player['proTeam']

        else:
            # Get team's players for this position
            team_players = []
            if position in players_by_position:
                for player in players_by_position[position]:
                    ranking_info = find_player_ranking(player['name'], position, rankings)
                    if ranking_info:
                        team_players.append(
                            {
                                'name': player['name'],
                                'team': player['proTeam'],  # Fix: use "proTeam" from the player data
                                'rank': ranking_info['rank'],
                                'owned_by': 'Team',
                            }
                        )

            # Get top 5 available players for this position
            available_players = available_by_position.get(position, [])

            # Sort available players and take top 5
            available_players.sort(key=lambda x: x['rank'])
            top_available = available_players[:5]

            # Add ownership info to available players
            for player in top_available:
                player['owned_by'] = 'Available'
                player['team'] = player['proTeam']  # Ensure consistency in key naming

        # Combine all players for this position
        all_players = team_players + top_available

        if not all_players:
            continue

        # Sort by rank
        all_players.sort(key=lambda x: x['rank'])

        safe_print(f'### {position}:')
        safe_print('')

        # Add position column for Flex rankings
        if position == 'Flex':
            safe_print('| Rank | Player | Team | Pos | Owner |')
            safe_print('|------|--------|------|-----|-------|')
        else:
            safe_print('| Rank | Player | Team | Owner |')
            safe_print('|------|--------|------|-------|')

        for player in all_players:
            rank = player['rank']
            name = player['name']
            team = player['team']
            owner = player['owned_by']

            # Owner formatting
            if owner == 'Team':
                owner_display = '🏆 Team'
            else:
                owner_display = '⚡ Free'

            # Format output based on position type
            if position == 'Flex':
                pos = player.get('position', position)
                safe_print(f'| {rank} | {name} | {team} | {pos} | {owner_display} |')
            else:
                safe_print(f'| {rank} | {name} | {team} | {owner_display} |')

        safe_print('')

    # Print unranked players on the roster
    safe_print('### Unranked Players on Roster')
    safe_print('')

    unranked_list = []

    for position, players in players_by_position.items():
        for player in players:
            # Check if player is ranked
            ranking_info = find_player_ranking(player['name'], position, rankings)
            if not ranking_info:
                unranked_list.append(
                    {
                        'name': player['name'],
                        'team': player['proTeam'],
                        'position': position,
                        'points': player['totalPoints'],
                    }
                )

    if unranked_list:
        safe_print('| Player | Team | Position | Points |')
        safe_print('|--------|------|----------|--------|')

        # Sort by points descending
        unranked_list.sort(key=lambda x: x['points'], reverse=True)

        for player in unranked_list:
            safe_print(f'| {player["name"]} | {player["team"]} | {player["position"]} | {player["points"]} |')
    else:
        safe_print('No unranked players found on roster.')

    safe_print('')


def output_rankings(
    team_name, scoring_type='half', league_type='espn', file_prefix=None, league_name=None, custom_owned_path=None
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

    Returns:
        bool: True if analysis completed successfully, False otherwise
    """

    safe_print(f'# 🏈 Analyzing team: {team_name}')
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

    # Load rankings
    safe_print('*Loading weekly rankings...*')
    safe_print('')
    rankings = load_rankings(scoring_type)

    if not rankings:
        safe_print('**No rankings found!**')
        return False

    # Show combined rankings (team's players + top 5 available by position)
    print_combined_position_rankings(players_by_position, all_owned_players, rankings, team_name, league_name)

    return True


def save_markdown():
    """Save the markdown content to start-sit.md"""
    output_file = Path(__file__).parent.parent / 'lineups' / 'start-sit.md'
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

        # Run analysis for this league
        success = output_rankings(
            team_name=league['team_name'],
            scoring_type=league['scoring_type'],
            league_type=league['platform'],
            file_prefix=f'{league["platform"]}_{league["league_id"]}',
            league_name=league['league_name'],
            custom_owned_path=league.get('custom_owned_file'),
        )

        if success:
            print(f'✅ Completed analysis for {league["team_name"]}')
        else:
            print(f'❌ Failed to analyze {league["team_name"]}')

    # Save the markdown content
    save_markdown()


if __name__ == '__main__':
    main()
