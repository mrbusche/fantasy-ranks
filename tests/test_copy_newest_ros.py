import os
from pathlib import Path
from unittest.mock import patch

from fantasy_ranks.copy_newest_ros import clean_csv_content, copy_newest_ros_file


def test_clean_csv_content_removes_bom(tmp_path):
    source = tmp_path / 'source.csv'
    destination = tmp_path / 'destination.csv'
    source.write_text('\ufeffRank,Player\n1,Josh Allen\n', encoding='utf-8')

    assert clean_csv_content(source, destination) is True
    assert destination.read_text(encoding='utf-8') == 'Rank,Player\n1,Josh Allen\n'


def test_clean_csv_content_falls_back_to_copy(tmp_path):
    source = tmp_path / 'source.csv'
    destination = tmp_path / 'destination.csv'
    source.write_text('Rank,Player\n1,Josh Allen\n', encoding='utf-8')

    with patch('builtins.open', side_effect=OSError('read failed')), patch('shutil.copy2') as copy:
        assert clean_csv_content(source, destination) is True
        copy.assert_called_once_with(source, destination)


def test_clean_csv_content_returns_false_when_copy_fails(tmp_path):
    source = tmp_path / 'source.csv'
    destination = tmp_path / 'destination.csv'
    source.write_text('Rank,Player\n1,Josh Allen\n', encoding='utf-8')

    with (
        patch('builtins.open', side_effect=OSError('read failed')),
        patch('shutil.copy2', side_effect=OSError('copy failed')),
    ):
        assert clean_csv_content(source, destination) is False


def test_copy_newest_ros_file_copies_latest_download(tmp_path):
    downloads = tmp_path / 'Downloads'
    downloads.mkdir()
    older = downloads / 'Top 150 old.csv'
    newest = downloads / 'Top 150 new.csv'
    older.write_text('old', encoding='utf-8')
    newest.write_text('\ufeffnew', encoding='utf-8')
    os.utime(older, (100, 100))
    os.utime(newest, (200, 200))

    with (
        patch('fantasy_ranks.copy_newest_ros.Path.home', return_value=tmp_path),
        patch('fantasy_ranks.copy_newest_ros.REST_OF_SEASON_RANKINGS_PATTERN', 'Top 150*.csv'),
        patch('fantasy_ranks.copy_newest_ros.clean_csv_content') as clean,
    ):
        copy_newest_ros_file()

    clean.assert_called_once_with(str(newest), Path('rankings/rest-of-season.csv'))


def test_copy_newest_ros_file_does_nothing_without_matches(tmp_path):
    with patch('fantasy_ranks.copy_newest_ros.Path.home', return_value=tmp_path):
        copy_newest_ros_file()


def test_copy_newest_ros_file_also_copies_2qb_pattern_when_configured(tmp_path):
    downloads = tmp_path / 'Downloads'
    downloads.mkdir()
    standard = downloads / 'Standard.csv'
    superflex = downloads / 'Superflex.csv'
    standard.write_text('standard', encoding='utf-8')
    superflex.write_text('superflex', encoding='utf-8')

    with (
        patch('fantasy_ranks.copy_newest_ros.Path.home', return_value=tmp_path),
        patch('fantasy_ranks.copy_newest_ros.REST_OF_SEASON_RANKINGS_PATTERN', 'Standard.csv'),
        patch('fantasy_ranks.copy_newest_ros.REST_OF_SEASON_RANKINGS_2QB_PATTERN', 'Superflex.csv'),
        patch('fantasy_ranks.copy_newest_ros.clean_csv_content') as clean,
    ):
        copy_newest_ros_file()

    clean.assert_any_call(str(standard), Path('rankings/rest-of-season.csv'))
    clean.assert_any_call(str(superflex), Path('rankings/rest-of-season-2qb.csv'))
    assert clean.call_count == 2


def test_copy_newest_ros_file_skips_2qb_when_pattern_not_set(tmp_path):
    downloads = tmp_path / 'Downloads'
    downloads.mkdir()
    standard = downloads / 'Standard.csv'
    standard.write_text('standard', encoding='utf-8')

    with (
        patch('fantasy_ranks.copy_newest_ros.Path.home', return_value=tmp_path),
        patch('fantasy_ranks.copy_newest_ros.REST_OF_SEASON_RANKINGS_PATTERN', 'Standard.csv'),
        patch('fantasy_ranks.copy_newest_ros.REST_OF_SEASON_RANKINGS_2QB_PATTERN', None),
        patch('fantasy_ranks.copy_newest_ros.clean_csv_content') as clean,
    ):
        copy_newest_ros_file()

    clean.assert_called_once_with(str(standard), Path('rankings/rest-of-season.csv'))


def test_copy_newest_ros_file_reports_copy_failure(tmp_path):
    downloads = tmp_path / 'Downloads'
    downloads.mkdir()
    source = downloads / 'Top 150.csv'
    source.write_text('data', encoding='utf-8')

    with (
        patch('fantasy_ranks.copy_newest_ros.Path.home', return_value=tmp_path),
        patch('fantasy_ranks.copy_newest_ros.clean_csv_content', return_value=False),
    ):
        copy_newest_ros_file()
