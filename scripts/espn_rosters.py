import argparse
import json
import os
from datetime import UTC, datetime, timedelta

from espn_api.football import League

# --- Default Configuration ---
DEFAULT_YEAR = 2026
SWID = os.environ.get('ESPN_SWID')
ESPN_S2 = os.environ.get('ESPN_S2')
ROSTERS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'rosters')


# Only refresh files once an hour by default
def file_needs_update(filepath, max_age_hours=1):
    """
    Check if a file needs to be updated based on its modification time.
    Returns True if the file doesn't exist or is older than max_age_hours.
    """
    if not os.path.exists(filepath):
        return True

    file_mod_time = datetime.fromtimestamp(os.path.getmtime(filepath), tz=UTC).astimezone()
    current_time = datetime.now(tz=UTC).astimezone()
    age_threshold = current_time - timedelta(hours=max_age_hours)

    return file_mod_time < age_threshold


def check_if_update_needed_for_league(league_id, ppr_type):
    """Check if the ESPN data file for this specific league needs updating."""
    owned_file = os.path.join(ROSTERS_DIR, f'espn_{league_id}_owned_players.json')

    owned_needs_update = file_needs_update(owned_file)

    if not owned_needs_update:
        owned_mod_time = datetime.fromtimestamp(os.path.getmtime(owned_file), tz=UTC).astimezone()

        print('✅ ESPN roster data is recent:')
        print(f'   - {owned_file}: {owned_mod_time.strftime("%Y-%m-%d %H:%M:%S")}')
        print('   Skipping ESPN API call to avoid rate limits')
        return False

    if owned_needs_update:
        print(f'📥 {owned_file} is outdated or missing - fetching fresh data...')

    return True


def fetch_and_export_data(league_id, year, ppr_type, swid=None, espn_s2=None):
    try:
        print(f'Connecting to League {league_id} ({year}) - {ppr_type.upper()} PPR...')
        league = League(league_id=league_id, year=year, swid=swid, espn_s2=espn_s2)
    except (ValueError, KeyError, RuntimeError) as e:
        print(f'Connection failed: {e}')
        return

    # --- 1. Process Owned Players ---
    print('Processing players on rosters...')
    owned_data = {}

    for team in league.teams:
        team_key = f'{team.team_name}'

        owned_data[team_key] = []

        for player in team.roster:
            player_info = {
                'name': player.name,
                'position': player.position,
                'proTeam': player.proTeam,
                'injured': player.injured,
                'totalPoints': player.total_points,
            }
            owned_data[team_key].append(player_info)

    # Create filename with league ID and PPR type
    os.makedirs(ROSTERS_DIR, exist_ok=True)
    filename = os.path.join(ROSTERS_DIR, f'espn_{league_id}_owned_players.json')
    with open(filename, 'w') as f:
        json.dump(owned_data, f, indent=4)
    print(f'✓ created {filename}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch ESPN league roster data')
    parser.add_argument('--league-id', type=int, help='ESPN League ID')
    parser.add_argument('--ppr', choices=['half', 'full'], default='half', help='PPR scoring type (default: half)')

    args = parser.parse_args()

    if check_if_update_needed_for_league(args.league_id, args.ppr):
        print('Fetching and exporting ESPN data...')
        fetch_and_export_data(args.league_id, DEFAULT_YEAR, args.ppr, SWID, ESPN_S2)
    else:
        print('No update needed - using existing data files.')
