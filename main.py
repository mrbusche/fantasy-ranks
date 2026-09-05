import json
import subprocess
import sys
from pathlib import Path


def load_league_config(config_file=None):
    """Load league configuration from JSON file."""
    if config_file is None:
        config_file = Path(__file__).parent / 'config.json'

    try:
        with open(config_file, encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f'Error: Configuration file {config_file} not found.')
        return None
    except json.JSONDecodeError:
        print(f'Error: Invalid JSON in configuration file {config_file}.')
        return None


def run_script(script_path, additional_args=None):
    """Run a Python script and handle any errors."""
    try:
        print(f'\n{"=" * 50}')
        print(f'Running: {script_path}')
        if additional_args:
            print(f'Arguments: {" ".join(additional_args)}')
        print(f'{"=" * 50}')

        cmd = [sys.executable, script_path]
        if additional_args:
            cmd.extend(additional_args)

        result = subprocess.run(
            cmd,
            capture_output=False,
            text=True,
            cwd=Path(__file__).parent,
            check=False,
        )

        if result.returncode == 0:
            print(f'✅ Successfully completed: {script_path}')
        else:
            print(f'❌ Error running {script_path}: Exit code {result.returncode}')

    except (OSError, ValueError, subprocess.SubprocessError) as e:
        print(f'❌ Failed to run {script_path}: {e}')


def run_platform_leagues(platform, leagues):
    """Run platform-specific script for multiple leagues."""
    platform_dir = Path(__file__).parent / platform
    script_path = f'{platform}_rosters.py'

    if not (platform_dir / script_path).exists():
        print(f'⚠️  Script not found: {platform_dir / script_path}')
        return

    for league_id, ppr_type, league_name in leagues:
        try:
            print(f'\n{"=" * 50}')
            print(f'Running: {platform_dir / script_path}')
            print(f'League: {league_name}')
            print(f'Arguments: --league-id {league_id} --ppr {ppr_type}')
            print(f'Working directory: {platform_dir}')
            print(f'{"=" * 50}')

            cmd = [
                sys.executable,
                script_path,
                '--league-id',
                league_id,
                '--ppr',
                ppr_type,
            ]

            result = subprocess.run(
                cmd,
                capture_output=False,
                text=True,
                cwd=platform_dir,
                check=False,
            )

            if result.returncode == 0:
                print(f'✅ Successfully completed: {league_name} ({platform})')
            else:
                print(
                    f'❌ Error running {league_name} ({platform}): Exit code {result.returncode}',
                )

        except (OSError, ValueError) as e:
            print(f'❌ Failed to run {league_name} ({platform}): {e}')


def main():
    """Main function to run all fantasy football scripts in sequence."""
    print('🏈 Fantasy Football Analysis Pipeline')
    print('Starting automated script execution...')

    # Load configuration from file for consistency
    leagues = load_league_config()
    if not leagues:
        print('❌ No leagues configured. Exiting.')
        return

    base_scripts = [
        'scripts/download_weekly_rankings.py',
    ]

    # Get the base directory (where main.py is located)
    base_dir = Path(__file__).parent

    # Run base scripts
    for script_relative_path in base_scripts:
        script_path = base_dir / script_relative_path

        if script_path.exists():
            run_script(str(script_path))
        else:
            print(f'⚠️  Script not found: {script_path}')

    # Group leagues by platform and run them
    platform_leagues = {}

    # Access the 'leagues' list from the dictionary
    for league in leagues['leagues']:
        platform = league['platform']
        league_id = league['league_id']
        ppr_type = league['scoring_type']
        league_name = league['league_name']

        if platform not in platform_leagues:
            platform_leagues[platform] = []
        platform_leagues[platform].append((league_id, ppr_type, league_name))

    # Run each platform's leagues
    for platform, leagues_data in platform_leagues.items():
        run_platform_leagues(platform, leagues_data)

    print(f'\n{"=" * 50}')
    print('🎯 All scripts completed!')
    print(f'{"=" * 50}')


if __name__ == '__main__':
    main()
