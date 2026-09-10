"""Create a markdown report of players owned by the configured teams."""

import json
from collections import defaultdict
from pathlib import Path

from fantasy_ranks.shared_functions import load_league_config, normalize_name

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROSTERS_DIR = PROJECT_ROOT / 'rosters'
OUTPUT_FILE = PROJECT_ROOT / 'rankings' / 'ownership.md'


def build_ownership_report(config, rosters_dir=ROSTERS_DIR):
    """Return markdown ownership rows for the configured team in each league."""
    ownership = defaultdict(set)
    display_names = {}

    for league in config['leagues']:
        league_id = str(league['league_id'])
        roster_key = f'{league["platform"]}_{league_id}'
        roster_file = rosters_dir / f'{roster_key}_owned_players.json'
        with roster_file.open(encoding='utf-8') as roster_handle:
            roster_data = json.load(roster_handle)

        team_name = league['team_name']
        team_players = roster_data[team_name]
        league_name = league.get('league_name') or roster_key
        seen_in_league = set()

        for player in team_players:
            player_name = player.get('name', '').strip()
            normalized_name = normalize_name(player_name)
            if not player_name or normalized_name in seen_in_league:
                continue

            seen_in_league.add(normalized_name)
            display_names.setdefault(normalized_name, player_name)
            ownership[normalized_name].add(league_name)

    rows = []
    for normalized_name in sorted(
        ownership,
        key=lambda name: (-len(ownership[name]), display_names[name].casefold()),
    ):
        leagues = '<br>'.join(sorted(ownership[normalized_name], key=str.casefold))
        rows.append((display_names[normalized_name], len(ownership[normalized_name]), leagues))
    return rows


def write_ownership_report(config, output_file=OUTPUT_FILE, rosters_dir=ROSTERS_DIR):
    """Write the configured-team ownership report and return its output path."""
    rows = build_ownership_report(config, rosters_dir)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        '# Player Ownership',
        '',
        'Players owned by the configured team in each league, grouped by ownership count.',
        '',
        '| Player Name | Owned Count | Leagues |',
        '| --- | ---: | --- |',
    ]
    lines.extend(f'| {name} | {count} | {leagues} |' for name, count, leagues in rows)
    output_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return output_file


def main():
    """Generate the ownership report from the project configuration."""
    config = load_league_config()
    if not config or not config.get('leagues'):
        print('❌ No valid leagues configured. Ownership report was not generated.')
        return

    output_file = write_ownership_report(config)
    print(f'✅ Ownership report written to {output_file}')


if __name__ == '__main__':
    main()
