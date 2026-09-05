from unittest.mock import MagicMock, patch

from main import main, run_platform_leagues, run_script


def test_run_script_success():
    mock_result = MagicMock(returncode=0)
    with patch('subprocess.run', return_value=mock_result) as mock_run:
        run_script('scripts/download_weekly_rankings.py', ['--test'])
        assert mock_run.called


def test_run_script_failure():
    mock_result = MagicMock(returncode=1)
    with patch('subprocess.run', return_value=mock_result):
        run_script('scripts/download_weekly_rankings.py')


def test_run_script_exception():
    with patch('subprocess.run', side_effect=OSError('Execution failed')):
        run_script('scripts/download_weekly_rankings.py')


def test_run_platform_leagues(tmp_path):
    # Test script not found
    with patch('main.Path') as mock_path:
        mock_path.return_value.parent.__truediv__.return_value = tmp_path
        run_platform_leagues('unknown_platform', [('123', 'half', 'My League')])

    # Test script exists and runs
    dummy_script = tmp_path / 'espn_rosters.py'
    dummy_script.write_text('# dummy', encoding='utf-8')
    mock_result = MagicMock(returncode=0)

    with patch('main.Path') as mock_path, patch('subprocess.run', return_value=mock_result) as mock_run:
        mock_path.return_value.parent.__truediv__.return_value = tmp_path
        run_platform_leagues('espn', [('123', 'half', 'My League')])
        assert mock_run.called


def test_main_no_config():
    with patch('main.load_league_config', return_value=None), patch('main.run_script') as mock_run_script:
        main()
        assert not mock_run_script.called


def test_main_success():
    config = {
        'leagues': [
            {'platform': 'espn', 'league_id': '123', 'scoring_type': 'half', 'league_name': 'ESPN League'},
            {'platform': 'sleeper', 'league_id': '456', 'scoring_type': 'full', 'league_name': 'Sleeper League'},
        ]
    }
    with (
        patch('main.load_league_config', return_value=config),
        patch('main.run_script') as mock_run_script,
        patch('main.run_platform_leagues') as mock_run_platform,
    ):
        main()
        # Should run base script download_weekly_rankings + output_rankings
        assert mock_run_script.call_count >= 2
        assert mock_run_platform.call_count == 2
