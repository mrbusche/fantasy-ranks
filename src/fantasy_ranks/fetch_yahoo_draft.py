"""Fetch a Yahoo! Fantasy Football draft results page and parse it into rosters.

Yahoo! has no public API, so this hits the same draft results page a user would
view in a browser (sorted by team) and extracts its visible text. See yahoo_web.py
for details on how the page is fetched and converted to plain text, and the README
for how to obtain a YAHOO_COOKIE value.
"""

import argparse
import sys

from fantasy_ranks.parse_yahoo_draft import parse_yahoo_draft
from fantasy_ranks.yahoo_web import ROSTERS_DIR, fetch_yahoo_page_text

DEFAULT_LEAGUE_ID = '960067'


def build_draft_results_url(league_id: str) -> str:
    return f'https://football.fantasysports.yahoo.com/f1/{league_id}/draftresults?drafttab=team&draft_results_period=current'


def fetch_yahoo_draft(league_id: str) -> str:
    """Download the Yahoo! draft results page for a league and save its text.

    Returns the path to the saved `rosters/yahoo_{league_id}.txt` file.
    """
    print(f'Fetching draft results for league {league_id} from Yahoo!...')
    cleaned_text = fetch_yahoo_page_text(build_draft_results_url(league_id))

    ROSTERS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = ROSTERS_DIR / f'yahoo_{league_id}.txt'
    output_path.write_text(cleaned_text, encoding='utf-8')

    print(f"Saved draft results text to '{output_path}'.")
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(description='Fetch and parse a Yahoo! league draft results page')
    parser.add_argument('league_id', nargs='?', default=DEFAULT_LEAGUE_ID, help='Yahoo! league ID')
    args = parser.parse_args()

    fetch_yahoo_draft(args.league_id)
    parse_yahoo_draft(args.league_id)


if __name__ == '__main__':
    sys.exit(main())
