#!/usr/bin/env python3
"""
Find the top 10 available players from Rest of Season rankings for each league.
Also shows the 10 lowest ranked players from a team.
"""

import csv
import os
from pathlib import Path

from dotenv import load_dotenv

from fantasy_ranks.shared_functions import (
    DEFAULT_LINEUP_SLOTS,
    build_normalized_name_index,
    get_all_owned_players,
    get_required_column,
    load_league_config,
    load_owned_players,
    names_match,
    normalize_name,
)

load_dotenv(Path(__file__).resolve().parents[2] / '.env')

# Glob patterns used by copy_newest_ros to populate the ROS rankings files below. Presence of
# REST_OF_SEASON_RANKINGS_2QB_PATTERN indicates a separate 2 QB/Superflex ROS file is expected;
# if it isn't set (or the file isn't there yet), we simply fall back to the standard rankings.
REST_OF_SEASON_RANKINGS_PATTERN = os.environ.get('REST_OF_SEASON_RANKINGS_PATTERN')
REST_OF_SEASON_RANKINGS_2QB_PATTERN = os.environ.get('REST_OF_SEASON_RANKINGS_2QB_PATTERN')

PLAYER_NAME_COLUMN = 'Player'
POSITION_COLUMN = 'Pos'
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


def is_player_owned(ros_player, all_owned_players, normalized_owned_players=None):
    """Check if a ROS player is owned by anyone across all teams."""
    player_name = ros_player['name']
    position = ros_player['position']

    # Direct name check
    if player_name in all_owned_players:
        return True

    # Normalize the ROS player name
    normalized_ros_name = normalize_name(player_name)

    if normalized_owned_players is None:
        normalized_owned_players = set(build_normalized_name_index(all_owned_players).keys())

    if normalized_ros_name in normalized_owned_players:
        return True

    normalized_owned_index = build_normalized_name_index(all_owned_players)
    if normalized_ros_name in normalized_owned_index:
        return True

    # Check against pre-normalized names to avoid repeating work.
    for normalized_owned_name in normalized_owned_players:
        # Check various matching scenarios
        if (
            normalized_ros_name == normalized_owned_name
            or normalized_ros_name in normalized_owned_name
            or normalized_owned_name in normalized_ros_name
            or (position == 'D/ST' and normalized_ros_name in normalized_owned_name)
            or (position == 'D/ST' and normalized_owned_name in normalized_ros_name)
        ):
            return True

    return False


def find_available_for_league(ros_rankings, owned_players):
    """Find available players for a specific league."""
    available_players = []
    normalized_owned_players = {normalize_name(name) for name in owned_players}

    for player in ros_rankings:
        if not is_player_owned(player, owned_players, normalized_owned_players):
            available_players.append(player)

    # Sort by rank and take top 10
    available_players.sort(key=lambda x: x['rank'])
    return available_players[:10]


def is_2qb_league(league):
    """Return True if a league starts 2+ QBs or uses a SUPERFLEX slot."""
    lineup_slots = league.get('lineup_slots') or DEFAULT_LINEUP_SLOTS
    return lineup_slots.get('SUPERFLEX', 0) > 0 or lineup_slots.get('QB', 0) >= 2


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


def format_improvement_action(top_available, bottom_10_team):
    """Create a concrete rest-of-season add/drop recommendation for a league."""
    if not top_available:
        return 'No ranked free agents are available; hold the roster and look for a trade to address weaknesses.'
    if not bottom_10_team:
        return f'Add **{top_available[0]["name"]} ({top_available[0]["position"]})** from free agency to improve the roster.'

    add_player = top_available[0]
    drop_player = bottom_10_team[0]
    drop_rank = drop_player['rank'] if drop_player['rank'] != 999 else 'NR'
    return (
        f'Add **{add_player["name"]} ({add_player["position"]})** and consider dropping '
        f'**{drop_player["name"]} ({drop_player["position"]})** '
        f'({add_player["rank"]} ROS rank vs. {drop_rank}).'
    )


def get_owned_players_by_league_with_teams(config):
    """Get owned players for each league separately, including team rosters."""
    base_dir = Path(__file__).resolve().parent.parent.parent
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
    base_dir = Path(__file__).resolve().parent.parent.parent
    ros_file = base_dir / 'rankings' / 'rest-of-season.csv'
    ros_2qb_file = base_dir / 'rankings' / 'rest-of-season-2qb.csv'

    print('🏈 Finding Top 10 Available Players by League from Rest of Season Rankings')
    print('=' * 80)

    # Load standard ROS rankings
    print(f'Loading ROS rankings from {ros_file}...')
    ros_rankings = load_ros_rankings(ros_file)

    if not ros_rankings:
        print('❌ Failed to load ROS rankings')
        return

    print(f'✅ Loaded {len(ros_rankings)} players from ROS rankings')

    # Load 2 QB/Superflex ROS rankings, if configured. Missing pattern/file never fails the run -
    # leagues that need it simply fall back to the standard rankings.
    ros_2qb_rankings = ros_rankings
    if not REST_OF_SEASON_RANKINGS_2QB_PATTERN:
        print('ℹ️  REST_OF_SEASON_RANKINGS_2QB_PATTERN not set; using standard rankings for 2 QB/Superflex leagues')
    elif not ros_2qb_file.exists():
        print(f'⚠️  {ros_2qb_file} not found; using standard rankings for 2 QB/Superflex leagues')
    else:
        print(f'Loading 2 QB/Superflex ROS rankings from {ros_2qb_file}...')
        loaded_2qb_rankings = load_ros_rankings(ros_2qb_file)
        if loaded_2qb_rankings:
            ros_2qb_rankings = loaded_2qb_rankings
            print(f'✅ Loaded {len(loaded_2qb_rankings)} players from 2 QB/Superflex ROS rankings')
        else:
            print('⚠️  Failed to load 2 QB/Superflex ROS rankings; using standard rankings instead')

    # Get owned players for each league
    print('\nGetting owned players for each league...')
    leagues_data, leagues_full_data = get_owned_players_by_league_with_teams(config)

    if not leagues_data:
        print('❌ No league data found')
        return

    # Prepare markdown content
    markdown_lines = [
        '# Fantasy Football Analysis\n',
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

        # Use 2 QB/Superflex rankings for leagues that start 2+ QBs or a SUPERFLEX slot.
        league_rankings = ros_2qb_rankings if is_2qb_league(league) else ros_rankings

        # Find top 10 available for this league
        top_available = find_available_for_league(league_rankings, owned_players)

        # Find team's players with rankings
        league_full_data = leagues_full_data[league_name]
        team_players_ranked = find_team_players_with_rankings(team_name, league_full_data, league_rankings)

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

        markdown_lines.append('\n### Action to Improve This Team\n')
        markdown_lines.append(f'{format_improvement_action(top_available, bottom_10_team)}\n')
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
