"""Shared helpers for fetching and extracting plain text from Yahoo! Fantasy Football pages.

Yahoo! has no public API, so these helpers hit the same pages a user would view in a
browser and extract their visible text, mirroring what you'd get by manually pressing
Ctrl+A / Ctrl+C on the page. Since these pages require an authenticated session, a Yahoo!
session cookie must be provided via the YAHOO_COOKIE environment variable (see .env / README).
"""

import os
from pathlib import Path

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / '.env')

YAHOO_COOKIE = os.environ.get('YAHOO_COOKIE')
ROSTERS_DIR = PROJECT_ROOT / 'rosters'

MISSING_COOKIE_MESSAGE = (
    'YAHOO_COOKIE environment variable is not set. Log into Yahoo! Fantasy Football in your '
    'browser, open developer tools, go to the Console tab, run `copy(document.cookie)`, and '
    'paste the copied value as YAHOO_COOKIE in your .env file. If requests still fail, instead '
    'copy the full "Cookie" request header from the Network tab (raw headers) or the '
    "Application/Storage tab's cookie list for football.fantasysports.yahoo.com."
)


def _extract_lines(node) -> list:
    """Walk the parsed HTML in document order, producing one line per row/heading.

    Table rows are rendered as tab-separated cells (matching how a browser's Ctrl+A/Ctrl+C
    copy of an HTML table pastes as tab-separated text), while other text nodes become their
    own line. This mirrors the plain-text format the Yahoo! parsers expect.
    """
    if isinstance(node, NavigableString):
        text = str(node).strip()
        return [text] if text else []

    if not isinstance(node, Tag) or node.name in ('script', 'style', 'noscript'):
        return []

    if node.name == 'table':
        lines = []
        for row in node.find_all('tr'):
            cells = [cell.get_text(' ', strip=True) for cell in row.find_all(['td', 'th'])]
            cells = [cell for cell in cells if cell]
            if cells:
                lines.append('\t'.join(cells))
        return lines

    lines = []
    for child in node.children:
        lines.extend(_extract_lines(child))
    return lines


def fetch_yahoo_page_text(url: str) -> str:
    """Download a Yahoo! Fantasy Football page and return its extracted plain text.

    Raises RuntimeError if YAHOO_COOKIE is not configured.
    """
    if not YAHOO_COOKIE:
        raise RuntimeError(MISSING_COOKIE_MESSAGE)

    headers = {
        'Cookie': YAHOO_COOKIE,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36',
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    body = soup.body or soup
    return '\n'.join(_extract_lines(body))
