import shutil
from pathlib import Path

# Target directories to remove relative to the project root
TARGET_DIRS = ['rankings', 'rosters', 'lineups']


def reset_project() -> None:
    # Resolve the project root (one level up from scripts/)
    scripts_dir = Path(__file__).resolve().parent
    project_root = scripts_dir.parent

    print(f'Project root: {project_root}')

    for dir_name in TARGET_DIRS:
        target_path = project_root / dir_name

        if target_path.is_dir():
            try:
                shutil.rmtree(target_path)
                print(f'Deleted: {target_path}')
            except OSError as error:
                print(f'Error removing {target_path}: {error}')
        else:
            print(f'Skipped (not found): {target_path}')


if __name__ == '__main__':
    reset_project()
