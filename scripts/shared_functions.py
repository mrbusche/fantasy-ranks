#!/usr/bin/env python3

import json
from pathlib import Path


def load_league_config(config_file=None):
    """Load league configuration from JSON file."""
    if config_file is None:
        config_file = Path(__file__).parent.parent / 'config.json'

    try:
        with open(config_file, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f'Error: Configuration file {config_file} not found.')
        return None
    except json.JSONDecodeError:
        print(f'Error: Invalid JSON in configuration file {config_file}.')
        return None
