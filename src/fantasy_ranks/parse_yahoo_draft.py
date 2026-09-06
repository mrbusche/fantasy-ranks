import json
import re
import sys


def parse_yahoo_draft(league_id: str):
    input_file = f'rosters/yahoo_{league_id}.txt'
    output_file = f'rosters/yahoo_{league_id}_owned_players.json'

    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Matches individual draft picks, e.g.: "1.	(1)	Jahmyr Gibbs (Det - RB)"
    pick_pattern = re.compile(r'^\d+\.\s*\(\d+\)\s*(.+?)\s*\([A-Za-z0-9/]+\s*-\s*([A-Za-z]+)\)\s*$')

    league_draft = {}
    last_potential_team = None
    current_team = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        pick_match = pick_pattern.match(line)
        if pick_match:
            # If we encounter the first pick of a new team, lock in the team header
            if line.startswith('1.') and last_potential_team:
                current_team = last_potential_team
                if current_team not in league_draft:
                    league_draft[current_team] = []
                last_potential_team = None

            if current_team:
                player_name, position = pick_match.groups()
                league_draft[current_team].append({'name': player_name.strip(), 'position': position.strip()})
        else:
            # Buffer non-pick lines; the one immediately preceding "1." is the team name
            last_potential_team = line

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(league_draft, f, indent=2, ensure_ascii=False)

    print(f"Parsed {len(league_draft)} teams into '{output_file}'.")


if __name__ == '__main__':
    league_id = sys.argv[1] if len(sys.argv) > 1 else '960067'
    parse_yahoo_draft(league_id)
