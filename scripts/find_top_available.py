#!/usr/bin/env python3
"""
Find the top 10 available players from Rest of Season rankings for each league.
Also shows the 10 lowest ranked players from a team.
"""

import csv
from pathlib import Path

from shared_functions import (
    get_all_owned_players,
    get_required_column,
    load_league_config,
    load_owned_players,
    names_match,
    normalize_name,
)

PLAYER_NAME_COLUMN = 'Player'
POSITION_COLUMN = 'Position'
RANK_COLUMN = 'Rank'
TEAM_COLUMN = 'Team'


def load_ros_rankings(csv_file):
    """Load the Rest of Season rankings from CSV file."""
    rankings = []

    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row in reader:
                player_name = get_required_column(row, PLAYER_NAME_COLUMN, 'PLAYER_NAME_COLUMN', reader).strip()
                rank = int(get_required_column(row, RANK_COLUMN, 'RANK_COLUMN', reader) or 0)
                team = get_required_column(row, TEAM_COLUMN, 'TEAM_COLUMN', reader).strip()
                position = get_required_column(row, POSITION_COLUMN, 'POSITION_COLUMN', reader).strip()

                rankings.append({'name': player_name, 'position': position, 'team': team, 'rank': rank})

    except Exception as e:
        print(f'Error loading {csv_file}: {e}')
        return []

    return rankings


def is_player_owned(ros_player, all_owned_players):
    """Check if a ROS player is owned by anyone across all teams."""
    player_name = ros_player['name']
    position = ros_player['position']

    # Direct name check
    if player_name in all_owned_players:
        return True

    # Normalize the ROS player name
    normalized_ros_name = normalize_name(player_name)

    # Check against all owned players
    for owned_name in all_owned_players:
        normalized_owned_name = normalize_name(owned_name)

        # Check various matching scenarios
        if (
            normalized_ros_name == normalized_owned_name
            or names_match(player_name, owned_name)
            or (position == 'D/ST' and normalized_ros_name in normalized_owned_name)
            or (position == 'D/ST' and normalized_owned_name in normalized_ros_name)
        ):
            return True

    return False


def find_available_for_league(ros_rankings, owned_players):
    """Find available players for a specific league."""
    available_players = []

    for player in ros_rankings:
        if not is_player_owned(player, owned_players):
            available_players.append(player)

    # Sort by rank and take top 10
    available_players.sort(key=lambda x: x['rank'])
    return available_players[:10]


def find_team_players_with_rankings(team_name, league_data, ros_rankings):
    """Find team players and their ROS rankings."""
    team_players_ranked = []

    if team_name not in league_data:
        return team_players_ranked

    team_players = league_data[team_name]

    for player in team_players:
        player_name = player.get('name', '').strip()

        # Find this player in ROS rankings
        for ros_player in ros_rankings:
            if player_name == ros_player['name'] or names_match(player_name, ros_player['name']):
                team_players_ranked.append(
                    {
                        'name': player_name,
                        'position': ros_player['position'],
                        'team': ros_player['team'],
                        'rank': ros_player['rank'],
                    }
                )
                break
        else:
            # Player not found in ROS rankings - assign high rank
            team_players_ranked.append(
                {
                    'name': player_name,
                    'position': player.get('position', 'Unknown'),
                    'team': player.get('proTeam', 'Unknown'),
                    'rank': 999,  # High rank for unranked players
                }
            )

    return team_players_ranked


def get_owned_players_by_league_with_teams(config):
    """Get owned players for each league separately, including team rosters."""
    base_dir = Path(__file__).parent.parent
    leagues_data = {}
    leagues_full_data = {}

    # Use passed config instead of loading again
    if not config or 'leagues' not in config:
        print('❌ Failed to load league configuration or no leagues found.')
        return {}, {}

    for league in config['leagues']:
        display_name = league.get('league_name', 'Unknown League')
        scoring_type = league.get('scoring_type')
        file_prefix = league['platform'] + '_' + league['league_id']

        if not scoring_type or not file_prefix:
            print(f'Warning: Skipping {display_name} - missing scoring_type or file_prefix')
            continue

        data_dir = base_dir / 'rosters'
        json_file = data_dir / f'{file_prefix}_owned_players.json'

        if json_file.exists():
            print(f'Loading {display_name}...')
            league_data = load_owned_players(json_file)
            if league_data:
                league_owned = get_all_owned_players(league_data)
                leagues_data[display_name] = league_owned
                leagues_full_data[display_name] = league_data
            else:
                print(f'Warning: Failed to load data from {json_file}')
        else:
            print(f'Warning: {json_file} not found')

    return leagues_data, leagues_full_data


def find_top_available_players(config):
    """Main function to find top 10 available players from ROS rankings for each league."""
    base_dir = Path(__file__).parent.parent
    ros_file = base_dir / 'rankings' / 'rest-of-season.csv'

    print('🏈 Finding Top 10 Available Players by League from Rest of Season Rankings')
    print('=' * 80)

    # Load ROS rankings
    print(f'Loading ROS rankings from {ros_file}...')
    ros_rankings = load_ros_rankings(ros_file)

    if not ros_rankings:
        print('❌ Failed to load ROS rankings')
        return

    print(f'✅ Loaded {len(ros_rankings)} players from ROS rankings')

    # Get owned players for each league
    print('\nGetting owned players for each league...')
    leagues_data, leagues_full_data = get_owned_players_by_league_with_teams(config)

    if not leagues_data:
        print('❌ No league data found')
        return

    # Prepare markdown content
    markdown_lines = [
        '# Fantasy Football Analysis:\n',
        '## Top 10 Available Players + Bottom 10 Team Players by League\n',
    ]

    # Analyze each league
    for league in config['leagues']:
        league_name = league.get('league_name', 'Unknown League')
        team_name = league.get('team_name', 'Unknown Team')

        if league_name not in leagues_data:
            print(f'⚠️  Skipping {league_name} - no data found')
            continue

        owned_players = leagues_data[league_name]

        print(f'\n📊 Analyzing {league_name}...')
        print(f'   Found {len(owned_players)} owned players')

        # Find top 10 available for this league
        top_available = find_available_for_league(ros_rankings, owned_players)

        # Find team's players with rankings
        league_full_data = leagues_full_data[league_name]
        team_players_ranked = find_team_players_with_rankings(team_name, league_full_data, ros_rankings)

        # Get bottom 10 team players (highest rank numbers = worst)
        team_players_ranked.sort(key=lambda x: x['rank'], reverse=True)
        bottom_10_team = team_players_ranked[:10]

        # Add to markdown
        markdown_lines.append(f'\n## {league_name} {team_name}\n')
        markdown_lines.append('### 🎯 Top 10 Available Players\n')
        markdown_lines.append('| Rank | Player | Position | Team |\n')
        markdown_lines.append('|------|--------|----------|------|\n')

        for player in top_available:
            markdown_lines.append(
                f'| {player["rank"]} | {player["name"]} | {player["position"]} | {player["team"]} |\n'
            )

        if bottom_10_team:
            markdown_lines.append(f'\n### 📉 Bottom 10 - {team_name}\n')
            markdown_lines.append('| Rank | Player | Position | Team |\n')
            markdown_lines.append('|------|--------|----------|------|\n')

            for player in bottom_10_team:
                rank_display = player['rank'] if player['rank'] != 999 else 'NR'
                markdown_lines.append(
                    f'| {rank_display} | {player["name"]} | {player["position"]} | {player["team"]} |\n'
                )

        markdown_lines.append(f'\n*{len(owned_players)} players owned in this league*\n')

    output_file = base_dir / 'lineups' / 'ros-analysis.md'

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.writelines(markdown_lines)

        print(f'\n✅ Results saved to {output_file}')

    except Exception as e:
        print(f'❌ Error saving to markdown: {e}')


if __name__ == '__main__':
    # Load league configuration once
    config = load_league_config()
    if not config or 'leagues' not in config:
        print('❌ Failed to load league configuration')

    find_top_available_players(config)
