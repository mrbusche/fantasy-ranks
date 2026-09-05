import csv
import os
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta

from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


def get_current_nfl_week(current_date=None):
    """Calculate the current NFL week based on Wednesday-Tuesday schedule."""
    week_1_start = datetime(2026, 9, 9, tzinfo=UTC)
    if current_date is None:
        current_date = datetime.now(UTC)

    # Calculate days since week 1 started
    days_since_week_1 = (current_date - week_1_start).days
    print(f'Days since week 1 started: {days_since_week_1}')

    # Calculate current week (each week is 7 days, starting Wednesday)
    current_week = 1 + (days_since_week_1 // 7)

    return max(1, min(current_week, 18))  # Clamp between weeks 1-18


def file_needs_update(filepath, max_age_hours=1):
    """Check if a file needs to be updated based on its modification time.
    Returns True if the file doesn't exist or is older than max_age_hours.
    """
    if not os.path.exists(filepath):
        return True

    file_mod_time = datetime.fromtimestamp(os.path.getmtime(filepath), tz=UTC)
    current_time = datetime.now(UTC)
    age_threshold = current_time - timedelta(hours=max_age_hours)

    return file_mod_time < age_threshold


def download_file(url, filename):
    """Downloads a file from a given URL and saves it with a specific filename.
    Removes any lines before the header row and filters to keep only specified columns.
    """
    try:
        print(f'Attempting to download {filename} from {url}...')
        # Use urlretrieve to download the file directly to a temporary location
        temp_filename = filename + '.tmp'
        urllib.request.urlretrieve(url, temp_filename)

        # Read the downloaded file and clean it
        with open(temp_filename, encoding='utf-8') as temp_file:
            lines = temp_file.readlines()

        # Find the header row and keep everything from that point
        header_found = False
        cleaned_lines = []

        for line in lines:
            # Check if this line starts with the header (with or without space in "Player Name")
            if line.strip().startswith('Rank,PlayerName') or line.strip().startswith(
                'Rank,Player Name',
            ):
                header_found = True

            if header_found:
                cleaned_lines.append(line)

        # Remove the temporary file
        os.remove(temp_filename)

        if not cleaned_lines:
            print(f'Error: No valid data found in {filename}')
            return

        # Parse CSV and filter columns
        temp_csv_file = filename + '.csv_temp'
        with open(temp_csv_file, 'w', encoding='utf-8', newline='') as temp_csv:
            temp_csv.writelines(cleaned_lines)

        # Read CSV and filter to keep only specified columns
        desired_columns = ['Rank', 'Player Name', 'Team', 'Position']

        with open(temp_csv_file, encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)

            # Handle different column name variations
            fieldnames = reader.fieldnames
            column_mapping = {}

            # Map actual column names to our desired names
            for desired in desired_columns:
                for actual in fieldnames:
                    if desired.lower().replace(' ', '') == actual.lower().replace(
                        ' ',
                        '',
                    ):
                        column_mapping[desired] = actual
                        break

            # Write filtered CSV
            with open(filename, 'w', encoding='utf-8', newline='') as output_file:
                writer = csv.DictWriter(output_file, fieldnames=desired_columns)
                writer.writeheader()

                for row in reader:
                    filtered_row = {}
                    for desired_col in desired_columns:
                        actual_col = column_mapping.get(desired_col)
                        if actual_col and actual_col in row:
                            filtered_row[desired_col] = row[actual_col]
                        else:
                            filtered_row[desired_col] = ''
                    writer.writerow(filtered_row)

        # Remove temporary CSV file
        os.remove(temp_csv_file)

        print(f'Successfully downloaded and filtered: {filename}')
        print(f'Saved to: {os.path.abspath(filename)}')
        print(f'Kept columns: {", ".join(desired_columns)}')

    except (
        OSError,
        urllib.error.URLError,
        csv.Error,
        UnicodeError,
        AttributeError,
        TypeError,
    ) as e:
        print(f'Error downloading {filename}: {e}')
    print('-' * 30)


def main():
    # Create rankings directory if it doesn't exist
    rankings_dir = 'rankings'
    if not os.path.exists(rankings_dir):
        os.makedirs(rankings_dir)
        print(f'Created directory: {rankings_dir}')

    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

    # Get current NFL week
    current_week = get_current_nfl_week()
    print(f'Using NFL Week {current_week}\n')

    # A list of tuples, where each tuple contains:
    # (name_from_prompt, url_to_download)
    url_template = os.environ.get('RANKINGS_URL')
    if not url_template:
        raise RuntimeError('RANKINGS_URL is not set. Add it to a .env file.')
    rankings_url = url_template.format(week=current_week)
    files_to_download = [
        (
            'half flex',
            f'{rankings_url}&position=FLX&scoring=HALF',
        ),
        (
            'ppr flex',
            f'{rankings_url}&position=FLX&scoring=PPR',
        ),
        (
            'qb',
            f'{rankings_url}&position=QB&scoring=PPR',
        ),
        (
            'dst',
            f'{rankings_url}&position=DST&scoring=PPR',
        ),
        (
            'kicker',
            f'{rankings_url}&position=K&scoring=PPR',
        ),
    ]

    print('Starting file downloads...\n')

    for name, url in files_to_download:
        # Create a valid filename
        # 1. Replace spaces with underscores
        # 2. Add the .csv extension
        filename = name.replace(' ', '_') + '.csv'

        # Create full path to save in rankings directory
        filepath = os.path.join(rankings_dir, filename)

        # Check if file needs updating
        if file_needs_update(filepath):
            print(f'📥 {filename} is outdated or missing - downloading...')
            # Call the download function
            download_file(url, filepath)
        else:
            file_mod_time = datetime.fromtimestamp(
                os.path.getmtime(filepath),
                tz=UTC,
            )
            print(
                f'✅ {filename} is recent (modified: {file_mod_time.strftime("%Y-%m-%d %H:%M:%S")}) - skipping download',
            )
            print('-' * 30)

    print('\nAll downloads finished.')


if __name__ == '__main__':
    main()
