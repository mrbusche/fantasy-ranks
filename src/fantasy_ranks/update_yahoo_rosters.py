import json
import re
import sys


def apply_yahoo_updates(league_id: str):
    json_file = f'rosters/yahoo_{league_id}_owned_players.json'
    updates_file = f'rosters/yahoo_updates_{league_id}.txt'

    with open(json_file, 'r', encoding='utf-8') as f:
        league_data = json.load(f)

    with open(updates_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Normalize special characters and whitespace
    text = content.replace('\xa0', ' ')

    # Regex matching player rows: Name Team - POS (optional injury tags like Q, IR, PUP, O, D)
    player_pattern = re.compile(r'^(.+?)\s+([A-Za-z0-9/]+)\s*-\s*([A-Za-z]+)(?:\s+[A-Z]+)?$')

    # Split transactions block using the date timestamp (e.g., 'Sep 2, 10:14 pm')
    date_split_pattern = re.compile(r'\b[A-Za-z]{3}\s+\d{1,2},\s+\d{1,2}:\d{2}\s+(?:am|pm)\b')

    # Process transactions in chronological order (Yahoo logs newest-first)
    chunks = []
    last_idx = 0
    for match in date_split_pattern.finditer(text):
        chunk = text[last_idx : match.start()]
        chunks.append(chunk)
        last_idx = match.end()

    # Reverse chunks so older transactions apply first
    for chunk in reversed(chunks):
        lines = [line.strip() for line in chunk.splitlines() if line.strip()]

        # Identify the team name (last non-empty line before the timestamp)
        if not lines:
            continue
        team_name = lines[-1]

        if team_name not in league_data:
            continue

        added_players = []
        dropped_players = []

        # Parse actions in the transaction block
        for i, line in enumerate(lines[:-1]):
            # Action: Added player (followed by Free Agent, Waiver, or Trade)
            if line in ('Free Agent', 'Waiver') or 'Trade' in line:
                prev_line = lines[i - 1]
                match = player_pattern.match(prev_line)
                if match:
                    added_players.append({'name': match.group(1).strip(), 'position': match.group(3).strip()})

            # Action: Dropped player (followed by To Waivers, To Free Agency, etc.)
            elif line in ('To Waivers', 'To Free Agency') or 'Drop' in line:
                prev_line = lines[i - 1]
                match = player_pattern.match(prev_line)
                if match:
                    dropped_players.append(match.group(1).strip())

        # Update the team roster
        roster = league_data[team_name]

        # 1. Remove dropped players
        if dropped_players:
            roster = [p for p in roster if p['name'] not in dropped_players]

        # 2. Add new players
        for new_player in added_players:
            if not any(p['name'] == new_player['name'] for p in roster):
                roster.append(new_player)

        league_data[team_name] = roster

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(league_data, f, indent=2, ensure_ascii=False)

    print(f"Rosters updated successfully in '{json_file}'.")


if __name__ == '__main__':
    league_id = sys.argv[1] if len(sys.argv) > 1 else '960067'
    apply_yahoo_updates(league_id)
