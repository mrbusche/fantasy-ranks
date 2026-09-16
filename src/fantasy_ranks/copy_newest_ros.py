import glob
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / '.env')
REST_OF_SEASON_RANKINGS_PATTERN = os.environ.get('REST_OF_SEASON_RANKINGS_PATTERN', 'Ranks*.csv')
REST_OF_SEASON_RANKINGS_2QB_PATTERN = os.environ.get('REST_OF_SEASON_RANKINGS_2QB_PATTERN')


def clean_csv_content(input_file, output_file):
    """Clean the CSV file by removing BOM and other weird characters."""
    try:
        # Read the original file with UTF-8-sig to handle BOM
        with open(input_file, 'r', encoding='utf-8-sig', newline='') as infile:
            # Read all content and clean it
            content = infile.read()

            # Remove any remaining BOM characters that might have slipped through
            content = content.replace('\ufeff', '')

            # Write cleaned content to destination
            with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
                outfile.write(content)

        print('✅ Cleaned CSV file and removed BOM/weird characters')
        return True

    except (OSError, UnicodeError, ValueError) as e:
        print(f'❌ Error cleaning CSV file: {e}')
        # Fall back to regular copy if cleaning fails
        try:
            shutil.copy2(input_file, output_file)
            print('⚠️  Fell back to regular copy due to cleaning error')
            return True
        except OSError as copy_error:
            print(f'❌ Error copying file: {copy_error}')
            return False


def copy_newest_matching_file(pattern, dest_filename):
    """Copy the newest file in Downloads matching `pattern` to `rankings/<dest_filename>`."""
    downloads_path = Path.home() / 'Downloads'

    full_pattern = str(downloads_path / str(pattern))

    matching_files = glob.glob(full_pattern)

    if not matching_files:
        print(f'❌ No matching files found in Downloads folder for pattern: {pattern}')
        return

    # Find the newest file based on modification time
    newest_file = max(matching_files, key=os.path.getmtime)

    # Create destination directory if it doesn't exist
    dest_dir = Path('rankings')
    os.makedirs(dest_dir, exist_ok=True)

    dest_path = dest_dir / dest_filename

    if clean_csv_content(newest_file, dest_path):
        print(f'Copied: {Path(newest_file).name} -> {dest_path}')
    else:
        print(f'Failed to copy {newest_file}')


def copy_newest_ros_file():
    copy_newest_matching_file(REST_OF_SEASON_RANKINGS_PATTERN, 'rest-of-season.csv')

    # 2 QB/Superflex rankings are optional - skip quietly if not configured so the rest of the
    # pipeline never fails because of a missing 2QB pattern/file.
    if REST_OF_SEASON_RANKINGS_2QB_PATTERN:
        copy_newest_matching_file(REST_OF_SEASON_RANKINGS_2QB_PATTERN, 'rest-of-season-2qb.csv')


if __name__ == '__main__':
    copy_newest_ros_file()
