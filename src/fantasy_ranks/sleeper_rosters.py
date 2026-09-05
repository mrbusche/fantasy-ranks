import argparse
import json
import os
import time
from pathlib import Path

import requests

# --- Configuration ---
# Cache settings
DATA_CACHE_DURATION = 3600  # 1 hour for rosters/free agents
MASTER_DB_CACHE_DURATION = 86400  # 24 hours for the huge player DB
FREE_AGENT_LIMIT = 200

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROSTERS_DIR = os.path.join(PROJECT_ROOT, 'rosters')
MASTER_PLAYERS_FILE = os.path.join(ROSTERS_DIR, 'sleeper_master_players.json')


def needs_refresh(filename, duration):
    if not os.path.exists(filename):
        return True
    return (time.time() - os.path.getmtime(filename)) > duration


def get_all_players_db():
    """
    Fetches the master Sleeper NFL player database.
    CAUTION: This is a large file (~50MB). cached for 24h.
    """
    if not needs_refresh(MASTER_PLAYERS_FILE, MASTER_DB_CACHE_DURATION):
        print('Loading master player database from cache...')
        with open(MASTER_PLAYERS_FILE, 'r') as f:
            return json.load(f)

    print('Downloading fresh master player database from Sleeper (this takes a moment)...')
    try:
        resp = requests.get('https://api.sleeper.app/v1/players/nfl')
        resp.raise_for_status()
        data = resp.json()
        os.makedirs(ROSTERS_DIR, exist_ok=True)
        with open(MASTER_PLAYERS_FILE, 'w') as f:
            json.dump(data, f)
        return data
    except (requests.RequestException, ValueError, OSError) as e:
        print(f'Failed to download player DB: {e}')
        return {}


def get_league_users(league_id):
    """Get user details to map owner_ids to team names."""
    url = f'https://api.sleeper.app/v1/league/{league_id}/users'
    resp = requests.get(url)
    resp.raise_for_status()
    users = resp.json()
    # Create a map of user_id -> display_name (team name)
    user_map = {}
    for u in users:
        # Use metadata team_name if available, fallback to display_name
        team_name = u.get('metadata', {}).get('team_name') or u.get('display_name') or 'Unknown Team'
        user_map[u['user_id']] = team_name.strip()
    return user_map


def get_league_rosters(league_id):
    url = f'https://api.sleeper.app/v1/league/{league_id}/rosters'
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()


def extract_player_data(player_id, player_db):
    """Helper to format player data cleanly from the master DB."""
    p_details = player_db.get(player_id, {})

    # Get position and normalize DEF to D/ST
    position = p_details.get('position', 'N/A')
    if position == 'DEF':
        position = 'D/ST'

    # Prefer injury_status (Questionable, Out, etc.) over status (Active, Inactive)
    status = p_details.get('injury_status') or p_details.get('status') or 'Inactive'

    return {
        'player_id': player_id,
        'name': f'{p_details.get("first_name", "")} {p_details.get("last_name", "")}'.strip(),
        'position': position,
        'nfl_team': p_details.get('team') or 'FA',
        'status': status,
        # search_rank is useful for sorting free agents later. Lower is better.
        'rank': p_details.get('search_rank') or 999999,
    }


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Sleeper Fantasy Football Roster Export')
    parser.add_argument('--league-id', required=True, help='Sleeper league ID')
    parser.add_argument(
        '--ppr',
        choices=['half', 'full', 'standard'],
        default='standard',
        help='PPR scoring type (for reference/future use)',
    )

    args = parser.parse_args()

    league_id = args.league_id

    # Files go in current directory (sleeper/) since script runs from there
    owned_file = os.path.join(ROSTERS_DIR, f'sleeper_{league_id}_owned_players.json')

    print(f'Processing Sleeper League {league_id} (PPR: {args.ppr})')

    # --- 1. Cache Check for Final Output ---
    if not needs_refresh(owned_file, DATA_CACHE_DURATION) and not needs_refresh(
        MASTER_PLAYERS_FILE, MASTER_DB_CACHE_DURATION
    ):
        age = time.time() - os.path.getmtime(owned_file)
        print(f'CACHE HIT: Sleeper data is recent. Next update in {int((DATA_CACHE_DURATION - age) / 60)} minutes.')
        return

    print(f'Starting Sleeper update for League {league_id}...')

    # --- 2. Load Master Data ---
    # We need this for EVERYTHING, so we load it first.
    player_db = get_all_players_db()
    if not player_db:
        print('Critical Error: Could not load player database.')
        return

    try:
        # --- 3. Fetch League Data ---
        print('Fetching league rosters and users...')
        users_map = get_league_users(league_id)
        rosters = get_league_rosters(league_id)

        owned_player_ids = set()
        final_roster_data = {}

        # --- 4. Process Rosters (Owned Players) ---
        print(f'Processing {len(rosters)} teams...')
        for roster in rosters:
            owner_id = roster.get('owner_id')
            # Some rosters might be orphaned, handle gracefully
            team_name = users_map.get(owner_id, f'Orphan Team {roster.get("roster_id")}')

            # 'players' is just a list of string IDs: ["4046", "8138", ...]
            team_player_ids = roster.get('players') or []

            team_cleaned_players = []
            for pid in team_player_ids:
                owned_player_ids.add(pid)
                # Build the player object
                p_data = extract_player_data(pid, player_db)
                is_starter = pid in (roster.get('starters') or [])
                p_data['roster_status'] = 'Starter' if is_starter else 'Bench'

                team_cleaned_players.append(p_data)

            final_roster_data[team_name] = team_cleaned_players

        # Save Owned
        os.makedirs(ROSTERS_DIR, exist_ok=True)
        with open(owned_file, 'w') as f:
            json.dump(final_roster_data, f, indent=4)
        print(f'SUCCESS: Saved rosters to {owned_file}')

    except (requests.RequestException, ValueError, OSError, TypeError, KeyError) as e:
        import traceback

        traceback.print_exc()
        print(f'An error occurred during Sleeper processing: {e}')


if __name__ == '__main__':
    main()
