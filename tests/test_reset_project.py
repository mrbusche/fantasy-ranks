from unittest.mock import patch

from fantasy_ranks.reset_project import reset_project


def test_reset_project_deletes_existing_and_skips_missing(tmp_path):
    rankings = tmp_path / 'rankings'
    rankings.mkdir()
    with patch('fantasy_ranks.reset_project.Path.resolve') as resolve:
        resolve.return_value.parent.parent.parent = tmp_path
        reset_project()

    assert not rankings.exists()


def test_reset_project_reports_delete_error(tmp_path):
    with (
        patch('fantasy_ranks.reset_project.Path.resolve') as resolve,
        patch('fantasy_ranks.reset_project.shutil.rmtree', side_effect=OSError('locked')),
    ):
        resolve.return_value.parent.parent.parent = tmp_path
        reset_project()
