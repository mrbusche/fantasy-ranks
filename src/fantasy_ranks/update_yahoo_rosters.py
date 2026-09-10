import json
import re
import sys

# Matches a single player entry within a transaction description, e.g. "T.J. Hockenson Min - TE"
_PLAYER_ENTRY = r'(?P<{prefix}_name>.+?)\s+(?P<{prefix}_team>[A-Za-z0-9/]+)\s*-\s*(?P<{prefix}_pos>[A-Za-z]+)'

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
    + r'\s+(?:To Waivers|To Free Agency|Trade)\s*)?$'
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
        added_player = {'name': match.group('added_name').strip(), 'position': match.group('added_pos').strip()}

    dropped_player_name = match.group('dropped_name').strip() if match.group('dropped_name') else None

    if not added_player and not dropped_player_name:
        return None

    return team_name, added_player, dropped_player_name


def apply_yahoo_updates(league_id: str):
    json_file = f'rosters/yahoo_{league_id}_owned_players.json'
    updates_file = f'rosters/yahoo_updates_{league_id}.txt'

    with open(json_file, 'r', encoding='utf-8') as f:
        league_data = json.load(f)

    with open(updates_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Normalize special characters
    text = content.replace('\xa0', ' ')

    # Individual transactions are tab-separated rows; everything else (section headers, the team
    # filter list, footer links, etc.) has no tabs and is ignored.
    transaction_rows = [line for line in text.splitlines() if '\t' in line]

    # Yahoo! lists the newest transaction first, so reverse to apply oldest first.
    for row in reversed(transaction_rows):
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
