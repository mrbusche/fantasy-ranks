from unittest.mock import MagicMock, patch

from fantasy_ranks.cli import main, run_module, run_platform_leagues


def test_run_module_success():
    mock_result = MagicMock(returncode=0)
    with patch('subprocess.run', return_value=mock_result) as mock_run:
        run_module('fantasy_ranks.download_weekly_rankings', ['--test'])
        assert mock_run.called


def test_run_module_failure():
    mock_result = MagicMock(returncode=1)
    with patch('subprocess.run', return_value=mock_result):
        run_module('fantasy_ranks.download_weekly_rankings')


def test_run_module_exception():
    with patch('subprocess.run', side_effect=OSError('Execution failed')):
        run_module('fantasy_ranks.download_weekly_rankings')


def test_run_module_subprocess_error():
    with patch('subprocess.run', side_effect=ValueError('invalid command')):
        run_module('fantasy_ranks.download_weekly_rankings')


def test_run_platform_leagues_unknown_platform():
    with patch('fantasy_ranks.cli.run_module') as mock_run_module:
        run_platform_leagues('yahoo', [('123', 'half', 'My League')])
        assert not mock_run_module.called


def test_run_platform_leagues_espn():
    with patch('fantasy_ranks.cli.run_module') as mock_run_module:
        run_platform_leagues('espn', [('123', 'half', 'My League')])
        mock_run_module.assert_called_once_with('fantasy_ranks.espn_rosters', ['--league-id', '123', '--ppr', 'half'])


def test_run_platform_leagues_sleeper():
    with patch('fantasy_ranks.cli.run_module') as mock_run_module:
        run_platform_leagues('sleeper', [('456', 'full', 'Sleeper League')])
        mock_run_module.assert_called_once_with(
            'fantasy_ranks.sleeper_rosters', ['--league-id', '456', '--ppr', 'full']
        )


def test_main_no_config():
    with (
        patch('fantasy_ranks.cli.load_league_config', return_value=None),
        patch('fantasy_ranks.cli.run_module') as mock_run_module,
    ):
        main()
        assert not mock_run_module.called


def test_main_success():
    config = {
        'leagues': [
            {'platform': 'espn', 'league_id': '123', 'scoring_type': 'half', 'league_name': 'ESPN League'},
            {'platform': 'sleeper', 'league_id': '456', 'scoring_type': 'full', 'league_name': 'Sleeper League'},
        ]
    }
    with (
        patch('fantasy_ranks.cli.load_league_config', return_value=config),
        patch('fantasy_ranks.cli.run_module') as mock_run_module,
        patch('fantasy_ranks.cli.run_platform_leagues') as mock_run_platform,
    ):
        main()
        # Should run download_weekly_rankings + output_rankings + copy_newest_ros + find_top_available
        assert mock_run_module.call_count == 4
        assert mock_run_platform.call_count == 2
