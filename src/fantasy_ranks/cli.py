"""Command-line entry point for the fantasy-ranks pipeline.

Orchestrates the full pipeline: download weekly rankings, pull rosters for
each configured league, build the start/sit report, refresh the rest-of-season
rankings, and find the top available free agents.
"""

import shutil
import subprocess
import sys
from pathlib import Path
from time import perf_counter

from fantasy_ranks.shared_functions import load_league_config

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PLATFORM_MODULES = {
    'espn': 'fantasy_ranks.espn_rosters',
    'sleeper': 'fantasy_ranks.sleeper_rosters',
    'yahoo': 'fantasy_ranks.fetch_yahoo_transactions',
}


def run_module(module_name, additional_args=None):
    """Run a package module as a script (`python -m <module>`) and report the outcome."""
    args = additional_args or []

    print(f'\n{"=" * 50}')
    print(f'Running: {module_name}')
    if args:
        print(f'Arguments: {" ".join(args)}')
    print(f'{"=" * 50}')

    cmd = [sys.executable, '-m', module_name, *args]

    try:
        result = subprocess.run(cmd, capture_output=False, text=True, cwd=PROJECT_ROOT, check=False)

        if result.returncode == 0:
            print(f'✅ Successfully completed: {module_name}')
        else:
            print(f'❌ Error running {module_name}: Exit code {result.returncode}')

    except (OSError, ValueError, subprocess.SubprocessError) as e:
        print(f'❌ Failed to run {module_name}: {e}')


def run_platform_leagues(platform, leagues):
    """Run the platform-specific roster fetch module for multiple leagues."""
    module_name = PLATFORM_MODULES.get(platform)

    if module_name is None:
        print(f'⚠️  Unknown platform: {platform}')
        return

    for league_id, ppr_type, league_name in leagues:
        print(f'\n{"=" * 50}')
        print(f'League: {league_name} ({platform})')
        print(f'{"=" * 50}')
        if platform == 'yahoo':
            # Yahoo! has no scoring-type-aware roster endpoint - just fetch and apply transactions.
            run_module(module_name, [str(league_id)])
        else:
            run_module(module_name, ['--league-id', str(league_id), '--ppr', ppr_type])


def format_markdown():
    """Format repository markdown files with `npm run fmt` or advise the user to run `npm ci`."""
    node_modules = PROJECT_ROOT / 'node_modules'
    if node_modules.exists():
        print(f'\n{"=" * 50}')
        print('Running: npm run fmt')
        print(f'{"=" * 50}')
        npm_bin = shutil.which('npm') or 'npm'
        try:
            subprocess.run([npm_bin, 'run', 'fmt'], cwd=PROJECT_ROOT, check=False)
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            print(f'❌ Failed to run npm run fmt: {e}')
    else:
        print('\n⚠️  node_modules does not exist. Run `npm ci` to format the markdown files in the repo on next run.')


def main() -> None:
    """Run the full fantasy football analysis pipeline in sequence."""
    start_time = perf_counter()

    print('🏈 Fantasy Football Analysis Pipeline')
    print('Starting automated script execution...')

    # Load configuration from file for consistency
    leagues = load_league_config()
    if not leagues:
        print('❌ No leagues configured. Exiting.')
        return

    run_module('fantasy_ranks.download_weekly_rankings')

    # Group leagues by platform and run them
    platform_leagues = {}
    for league in leagues['leagues']:
        platform = league['platform']
        league_id = league['league_id']
        ppr_type = league['scoring_type']
        league_name = league.get('league_name', '')
        platform_leagues.setdefault(platform, []).append((league_id, ppr_type, league_name))

    for platform, leagues_data in platform_leagues.items():
        run_platform_leagues(platform, leagues_data)

    run_module('fantasy_ranks.output_rankings')
    run_module('fantasy_ranks.copy_newest_ros')
    run_module('fantasy_ranks.find_top_available')
    run_module('fantasy_ranks.ownership')

    format_markdown()

    print(f'\n{"=" * 50}')
    print(f'🎯 All scripts completed! Total time: {perf_counter() - start_time:.2f} seconds')
    print(f'{"=" * 50}')


if __name__ == '__main__':
    main()
