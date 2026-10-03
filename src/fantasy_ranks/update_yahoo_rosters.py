import json
import re
import sys

# Matches a single player entry within a transaction description, e.g. "T.J. Hockenson Min - TE"
# Yahoo may include a player status marker such as IR/Q/O after the position before the action.
_PLAYER_ENTRY = (
    r'(?P<{prefix}_name>.+?)\s+'
    r'(?P<{prefix}_team>[A-Za-z0-9/]+)\s*-\s*'
    r'(?P<{prefix}_pos>[A-Za-z]+)'
    r'(?:\s+(?P<{prefix}_status>[A-Z]{{1,5}}))?'
)

# Matches a full transaction description, e.g.:
#   "T.J. Hockenson Min - TE Free Agent Dalton Kincaid Buf - TE To Waivers"  (waiver claim: add + drop)
#   "Michael Mayer LV - TE Free Agent"                                      (add only)
#   "Dalton Kincaid Buf - TE To Waivers"                                    (drop only)
# Both halves are optional since a row may only add or only drop a player.
TRANSACTION_PATTERN = re.compile(
    r'^(?:'
    + _PLAYER_ENTRY.format(prefix='added')
    + r'\s+(?:Free Agent|Waiver|Trade)\s*)?'
    + r'(?:'
    + _PLAYER_ENTRY.format(prefix='dropped')
    + r'(?:\s+[A-Z]{1,3})?\s+(?:To Waivers|To Free Agency|Trade)\s*)?$'
)

# Matches the trailing timestamp on a transaction row, e.g. "Sep 9, 4:51 pm"
DATE_PATTERN = re.compile(r'\b[A-Za-z]{3}\s+\d{1,2},\s+\d{1,2}:\d{2}\s+(?:am|pm)\b')


def parse_transaction_row(row: str):
    """Parse a single tab-separated Yahoo! transaction row.

    Rows look like (tab-separated cells): ' \tT.J. Hockenson Min - TE Free Agent Dalton Kincaid Buf - TE To
    Waivers\tRunitback Sep 9, 4:51 pm', where the last cell is the team name followed by a timestamp.

    Returns a (team_name, added_player, dropped_player_name) tuple, where added_player is a
    {'name', 'position'} dict or None, and dropped_player_name is a string or None. Returns None
    if the row isn't a recognizable transaction (e.g. a section header with no tabs).
    """
    fields = [field.strip() for field in row.split('\t') if field.strip()]
    if len(fields) < 2:
        return None

    description, team_and_date = fields[-2], fields[-1]

    date_match = DATE_PATTERN.search(team_and_date)
    team_name = team_and_date[: date_match.start()].strip() if date_match else team_and_date.strip()

    match = TRANSACTION_PATTERN.match(description)
    if not match:
        return None

    added_player = None
    if match.group('added_name'):
        added_player = _normalize_defense_name(
            {'name': match.group('added_name').strip(), 'position': match.group('added_pos').strip()}
        )

    dropped_player_name = match.group('dropped_name').strip() if match.group('dropped_name') else None
    if dropped_player_name:
        dropped_player_name = _DEFENSE_NICKNAMES.get(dropped_player_name, dropped_player_name)

    if not added_player and not dropped_player_name:
        return None

    return team_name, added_player, dropped_player_name


_DEFENSE_NICKNAMES = {
    'Arizona': 'Cardinals', 'Atlanta': 'Falcons', 'Baltimore': 'Ravens', 'Buffalo': 'Bills',
    'Carolina': 'Panthers', 'Chicago': 'Bears', 'Cincinnati': 'Bengals', 'Cleveland': 'Browns',
    'Dallas': 'Cowboys', 'Denver': 'Broncos', 'Detroit': 'Lions', 'Green Bay': 'Packers',
    'Houston': 'Texans', 'Indianapolis': 'Colts', 'Jacksonville': 'Jaguars', 'Kansas City': 'Chiefs',
    'Las Vegas': 'Raiders', 'Los Angeles Chargers': 'Chargers', 'Los Angeles Rams': 'Rams',
    'Miami': 'Dolphins', 'Minnesota': 'Vikings', 'New England': 'Patriots', 'New Orleans': 'Saints',
    'New York Giants': 'Giants', 'New York Jets': 'Jets', 'Philadelphia': 'Eagles', 'Pittsburgh': 'Steelers',
    'San Francisco': '49ers', 'Seattle': 'Seahawks', 'Tampa Bay': 'Buccaneers', 'Tennessee': 'Titans',
    'Washington': 'Commanders',
}  # fmt: skip


def _normalize_defense_name(player: dict) -> dict:
    """Yahoo! defenses are named by nickname (e.g. 'Packers'); map any city-style name to match."""
    if player.get('position') in ('DEF', 'D/ST') and player['name'] in _DEFENSE_NICKNAMES:
        return {**player, 'name': _DEFENSE_NICKNAMES[player['name']]}
    return player


def _dedupe_roster(roster: list) -> list:
    seen = set()
    result = []
    for player in map(_normalize_defense_name, roster):
        if player['name'] not in seen:
            seen.add(player['name'])
            result.append(player)
    return result


def parse_trade_row(row: str):
    """Parse a Yahoo! trade row, e.g. ' \tAaron Jones Sr. Min - RB\tTraded to\tGarth Brooks Oct 2, 3:14 am'.

    Returns (destination_team, player_dict) or None if the row isn't a trade.
    """
    fields = [field.strip() for field in row.split('\t') if field.strip()]
    if len(fields) < 3 or fields[-2].lower() != 'traded to':
        return None

    match = re.match(_PLAYER_ENTRY.format(prefix='p') + r'$', fields[-3])
    if not match:
        return None

    team_and_date = fields[-1]
    date_match = DATE_PATTERN.search(team_and_date)
    team_name = team_and_date[: date_match.start()].strip() if date_match else team_and_date.strip()
    return team_name, {'name': match.group('p_name').strip(), 'position': match.group('p_pos').strip()}


def apply_yahoo_updates(league_id: str):
    json_file = f'rosters/yahoo_{league_id}_owned_players.json'
    updates_file = f'rosters/yahoo_updates_{league_id}.txt'

    with open(json_file, 'r', encoding='utf-8') as f:
        league_data = json.load(f)
    league_data = {team: _dedupe_roster(roster) for team, roster in league_data.items()}

    with open(updates_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Normalize special characters
    text = content.replace('\xa0', ' ')

    # Individual transactions are tab-separated rows; everything else (section headers, the team
    # filter list, footer links, etc.) has no tabs and is ignored.
    transaction_rows = [line for line in text.splitlines() if '\t' in line]

    # Yahoo! lists the newest transaction first, so reverse to apply oldest first.
    for row in reversed(transaction_rows):
        trade = parse_trade_row(row)
        if trade is not None:
            to_team, player = trade
            if to_team not in league_data:
                continue
            # The row only names the destination, so remove the player from whichever team had him.
            for team, team_roster in league_data.items():
                if team != to_team:
                    league_data[team] = [p for p in team_roster if p['name'] != player['name']]
            if not any(p['name'] == player['name'] for p in league_data[to_team]):
                league_data[to_team].append(player)
            continue

        parsed = parse_transaction_row(row)
        if parsed is None:
            continue

        team_name, added_player, dropped_player_name = parsed
        if team_name not in league_data:
            continue

        roster = league_data[team_name]

        # 1. Remove the dropped player
        if dropped_player_name:
            roster = [p for p in roster if p['name'] != dropped_player_name]

        # 2. Add the new player
        if added_player and not any(p['name'] == added_player['name'] for p in roster):
            roster.append(added_player)

        league_data[team_name] = roster

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(league_data, f, indent=2, ensure_ascii=False)

    print(f"Rosters updated successfully in '{json_file}'.")


if __name__ == '__main__':
    league_id = sys.argv[1] if len(sys.argv) > 1 else '960067'
    apply_yahoo_updates(league_id)
