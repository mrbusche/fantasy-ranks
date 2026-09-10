"""Fetch a Yahoo! Fantasy Football transactions page and apply it to local rosters.

Yahoo! has no public API, so this hits the same transactions page a user would view
in a browser and extracts its visible text. See yahoo_web.py for details on how the
page is fetched and converted to plain text, and the README for how to obtain a
YAHOO_COOKIE value.

This is the script that runs automatically as part of the `fantasy-ranks` pipeline
so locally maintained Yahoo! roster JSON files stay up to date with waiver/trade
activity, without requiring a manual copy/paste of the transactions page.
"""

import argparse
import sys

from fantasy_ranks.fetch_yahoo_draft import fetch_yahoo_draft
from fantasy_ranks.parse_yahoo_draft import parse_yahoo_draft
from fantasy_ranks.update_yahoo_rosters import apply_yahoo_updates
from fantasy_ranks.yahoo_web import ROSTERS_DIR, fetch_yahoo_page_text

DEFAULT_LEAGUE_ID = '101202'


def build_transactions_url(league_id: str) -> str:
    return f'https://football.fantasysports.yahoo.com/f1/{league_id}/transactions'


def fetch_yahoo_transactions(league_id: str) -> str:
    """Download the Yahoo! transactions page for a league and save its text.

    Returns the path to the saved `rosters/yahoo_updates_{league_id}.txt` file.
    """
    print(f'Fetching transactions for league {league_id} from Yahoo!...')
    cleaned_text = fetch_yahoo_page_text(build_transactions_url(league_id))

    ROSTERS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = ROSTERS_DIR / f'yahoo_updates_{league_id}.txt'
    output_path.write_text(cleaned_text, encoding='utf-8')

    print(f"Saved transactions text to '{output_path}'.")
    return str(output_path)


def update_yahoo_league(league_id: str) -> None:
    """Fetch transactions for a league and apply them to its local roster JSON file.

    If the roster JSON doesn't exist yet, imports the draft first (equivalent to
    running `fetch_yahoo_draft` then `parse_yahoo_draft`) so transactions have a
    roster to apply against.
    """
    fetch_yahoo_transactions(league_id)

    owned_players_file = ROSTERS_DIR / f'yahoo_{league_id}_owned_players.json'
    if not owned_players_file.exists():
        print(f"'{owned_players_file}' does not exist yet - importing the draft first...")
        fetch_yahoo_draft(league_id)
        parse_yahoo_draft(league_id)

    apply_yahoo_updates(league_id)


def main():
    parser = argparse.ArgumentParser(description='Fetch and apply a Yahoo! league transactions page')
    parser.add_argument('league_id', nargs='?', default=DEFAULT_LEAGUE_ID, help='Yahoo! league ID')
    args = parser.parse_args()

    update_yahoo_league(args.league_id)


if __name__ == '__main__':
    sys.exit(main())
