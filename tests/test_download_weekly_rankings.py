import os
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from fantasy_ranks.download_weekly_rankings import (
    download_file,
    file_needs_update,
    get_current_nfl_week,
    main,
)


@pytest.mark.parametrize(
    'test_date,expected_week',
    [
        (datetime(2026, 9, 5, 12, 0, tzinfo=UTC), 1),
        (datetime(2026, 9, 8, 23, 59, tzinfo=UTC), 1),
        (datetime(2026, 9, 9, 0, 0, tzinfo=UTC), 1),
        (datetime(2026, 9, 15, 23, 59, tzinfo=UTC), 1),
        (datetime(2026, 9, 16, 0, 0, tzinfo=UTC), 2),
        (datetime(2026, 9, 22, 23, 59, tzinfo=UTC), 2),
        (datetime(2026, 9, 23, 0, 0, tzinfo=UTC), 3),
        (datetime(2026, 9, 30, 0, 0, tzinfo=UTC), 4),
        (datetime(2027, 1, 6, 0, 0, tzinfo=UTC), 18),
        (datetime(2027, 2, 1, 0, 0, tzinfo=UTC), 18),
    ],
)
def test_get_current_nfl_week_dates(test_date, expected_week):
    assert get_current_nfl_week(test_date) == expected_week


def test_get_current_nfl_week_default_now():
    week = get_current_nfl_week()
    assert 1 <= week <= 18


def test_file_needs_update_non_existent(tmp_path):
    missing_file = str(tmp_path / 'missing.csv')
    assert file_needs_update(missing_file) is True


def test_file_needs_update_recent(tmp_path):
    test_file = tmp_path / 'recent.csv'
    test_file.write_text('content', encoding='utf-8')
    assert file_needs_update(str(test_file), max_age_hours=1) is False


def test_file_needs_update_old(tmp_path):
    test_file = tmp_path / 'old.csv'
    test_file.write_text('content', encoding='utf-8')
    # Set modification time to 2 hours ago
    past_time = datetime.now(UTC).timestamp() - 7200
    os.utime(str(test_file), (past_time, past_time))
    assert file_needs_update(str(test_file), max_age_hours=1) is True


def test_download_file_success(tmp_path):
    output_file = str(tmp_path / 'rankings.csv')
    dummy_csv_content = (
        'Some junk line at the top\n'
        'Another junk line\n'
        'Rank,Player Name,Team,Position,IgnoredCol\n'
        '1,Josh Allen,BUF,QB,100\n'
        '2,Patrick Mahomes,KC,QB,90\n'
    )

    def mock_urlretrieve(url, filename):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(dummy_csv_content)

    with patch('urllib.request.urlretrieve', side_effect=mock_urlretrieve):
        download_file('http://example.com/data.csv', output_file)

    assert os.path.exists(output_file)
    with open(output_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    assert lines[0].strip() == 'Rank,Player Name,Team,Position'
    assert lines[1].strip() == '1,Josh Allen,BUF,QB'
    assert lines[2].strip() == '2,Patrick Mahomes,KC,QB'


def test_download_file_header_variant_no_space(tmp_path):
    output_file = str(tmp_path / 'rankings_no_space.csv')
    dummy_csv_content = 'Rank,PlayerName,Team,Position\n1,Justin Jefferson,MIN,WR\n'

    def mock_urlretrieve(url, filename):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(dummy_csv_content)

    with patch('urllib.request.urlretrieve', side_effect=mock_urlretrieve):
        download_file('http://example.com/data.csv', output_file)

    assert os.path.exists(output_file)
    with open(output_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    assert lines[0].strip() == 'Rank,Player Name,Team,Position'
    assert lines[1].strip() == '1,Justin Jefferson,MIN,WR'


def test_download_file_no_valid_data(tmp_path):
    output_file = str(tmp_path / 'empty.csv')

    def mock_urlretrieve(url, filename):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('Invalid,Data,Only\n1,2,3\n')

    with patch('urllib.request.urlretrieve', side_effect=mock_urlretrieve):
        download_file('http://example.com/data.csv', output_file)

    assert not os.path.exists(output_file)


def test_download_file_fills_missing_columns(tmp_path):
    output_file = str(tmp_path / 'missing-column.csv')

    def mock_urlretrieve(url, filename):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('Rank,Player Name\n1,Josh Allen\n')

    with patch('urllib.request.urlretrieve', side_effect=mock_urlretrieve):
        download_file('http://example.com/data.csv', output_file)

    assert open(output_file, encoding='utf-8').read().splitlines()[1] == '1,Josh Allen,,'


def test_download_file_network_error(tmp_path):
    output_file = str(tmp_path / 'failed.csv')
    with patch('urllib.request.urlretrieve', side_effect=OSError('Network unreachable')):
        download_file('http://example.com/data.csv', output_file)

    assert not os.path.exists(output_file)


def test_main_raises_when_env_not_set(monkeypatch):
    monkeypatch.delenv('RANKINGS_URL', raising=False)
    with (
        patch('fantasy_ranks.download_weekly_rankings.load_dotenv'),
        pytest.raises(RuntimeError, match='RANKINGS_URL is not set'),
    ):
        main()


def test_main_success(monkeypatch, tmp_path):
    monkeypatch.setenv('RANKINGS_URL', 'http://example.com/rankings?week={week}')
    with (
        patch('fantasy_ranks.download_weekly_rankings.load_dotenv'),
        patch('fantasy_ranks.download_weekly_rankings.file_needs_update', return_value=True),
        patch('fantasy_ranks.download_weekly_rankings.download_file') as mock_download,
        patch('os.makedirs'),
    ):
        main()
        assert mock_download.call_count == 5


def test_main_files_already_recent(monkeypatch):
    monkeypatch.setenv('RANKINGS_URL', 'http://example.com/rankings?week={week}')
    with (
        patch('fantasy_ranks.download_weekly_rankings.load_dotenv'),
        patch('fantasy_ranks.download_weekly_rankings.file_needs_update', return_value=False),
        patch('fantasy_ranks.download_weekly_rankings.download_file') as mock_download,
        patch('os.path.getmtime', return_value=1700000000),
        patch('os.makedirs'),
    ):
        main()
        assert mock_download.call_count == 0
