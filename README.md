# Fantasy Ranks

Generate lineups for your Sleeper and ESPN leagues

## Prerequisites

- Python 3.13+ (see `.python-version` for the exact version this project is developed against)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) for dependency management and running scripts

## Installation

1. Clone the repository:

   ```shell
   git clone https://github.com/mrbusche/fantasy-ranks.git
   cd fantasy-ranks
   ```

2. Install dependencies:

   ```shell
   uv sync
   ```

## Setup

Create a file named `config.json` in the root. It must be valid JSON containing a `leagues` array; separate multiple leagues with a comma. Each league is validated when loaded, and invalid entries are skipped with a warning, so every field below must match its expected format:

```json
{
  "leagues": [
    {
      "platform": "", # required: "espn", "sleeper", or "yahoo"
      "league_id": "", # required: numeric, get this from the website URL
      "scoring_type": "", # required: "half" or "full"
      "team_name": "", # required: your exact team name in the league
      "league_name": "" # optional, but will help differentiate leagues in output
    }
  ]
}
```

Create a `.env` file in the root:

```text
RANKINGS_URL=https://some-website.com?week={week}&export=csv

# Only required for private ESPN leagues
ESPN_SWID={your-espn-swid}
ESPN_S2=your-espn-s2-value
```

- `RANKINGS_URL`: if you found this website you can figure out how your favorite rankings site exposes their rankings, you will want this exported as csv.
- `ESPN_SWID` / `ESPN_S2`: only needed if any configured league is a private ESPN league. Log in to ESPN in your browser, open dev tools, and copy the `espn_s2` and `SWID` cookie values (`SWID` includes the surrounding curly braces).

## Generating lineups

```shell
uv run fantasy-ranks
```

This downloads the latest weekly rankings, pulls your rosters from ESPN and Sleeper, uses the manually maintained Yahoo! roster files, and writes the resulting analysis to `lineups/start-sit.md`.

## Importing Yahoo! rosters

Yahoo! leagues are kept up to date manually. To import or refresh a Yahoo! draft roster, open the draft results page, copy the entire page (press `Ctrl + A`, then `Ctrl + C`), and save the copied text to:

```text
rosters/yahoo_{leagueId}.txt
```

Then run the parser with your league ID:

```shell
uv run python src\fantasy_ranks\parse_yahoo_draft.py {leagueId}
```

The generated `rosters/yahoo_{leagueId}_owned_players.json` file is treated as the source of truth. The main `fantasy-ranks` command does not run the Yahoo! parser automatically.

### Updating Yahoo! rosters after waivers

After waivers or other roster changes, open the Yahoo! transactions page, copy the entire page (press `Ctrl + A`, then `Ctrl + C`), and save the copied text to:

```text
rosters/yahoo_updates_{leagueId}.txt
```

Then update the local roster file by running:

```shell
uv run python src\fantasy_ranks\update_yahoo_rosters.py {leagueId}
```

You can copy and process the same transactions page more than once. Reprocessing transactions is safe: players are not added if they are already on the roster, and dropping a player who has already been removed has no additional effect.

## Resetting the project

To clear out generated data (`rankings/`, `rosters/`, and `lineups/` directories) and start fresh:

```shell
uv run python -m fantasy_ranks.reset_project
```

## Running tests

```shell
uv run pytest
```

## Project structure

- `src/fantasy_ranks/` — the installable package: `cli.py` orchestrates the pipeline, and each module (`espn_rosters.py`, `sleeper_rosters.py`, `download_weekly_rankings.py`, `output_rankings.py`, `copy_newest_ros.py`, `find_top_available.py`, `reset_project.py`, `shared_functions.py`) can also be run standalone via `uv run python -m fantasy_ranks.<module>`.
- `tests/` — mirrors the package modules, with shared fixtures for mocking ESPN/Sleeper API calls in `tests/conftest.py`.

## Sample Output - start-sit.md

### COMBINED RANKINGS: MY LEAGUE THE SHERIFF + TOP 5 AVAILABLE BY POSITION

#### QB

| Rank | Player         | Team | Owner   |
| ---- | -------------- | ---- | ------- |
| 1    | Lamar Jackson  | BAL  | 🏆 Team |
| 6    | Baker Mayfield | TB   | ⚡ Free |
| 9    | Kyler Murray   | MIN  | ⚡ Free |
| 13   | Jordan Love    | GB   | ⚡ Free |
| 14   | Daniel Jones   | IND  | ⚡ Free |
| 15   | Justin Fields  | KC   | ⚡ Free |

#### RB

| Rank | Player             | Team | Owner   |
| ---- | ------------------ | ---- | ------- |
| 3    | Bijan Robinson     | ATL  | 🏆 Team |
| 16   | James Conner       | ARI  | ⚡ Free |
| 22   | Alvin Kamara       | NO   | ⚡ Free |
| 27   | Kenneth Walker III | KC   | 🏆 Team |
| 40   | Tyrone Tracy Jr.   | NYG  | ⚡ Free |
| 52   | Isiah Pacheco      | DET  | ⚡ Free |
| 57   | Jerome Ford        | WAS  | ⚡ Free |
| 68   | J.K. Dobbins       | DEN  | 🏆 Team |

#### WR

| Rank | Player            | Team | Owner   |
| ---- | ----------------- | ---- | ------- |
| 23   | Tee Higgins       | CIN  | 🏆 Team |
| 26   | Amon-Ra St. Brown | DET  | 🏆 Team |
| 44   | Jerry Jeudy       | CLE  | ⚡ Free |
| 63   | Calvin Ridley     | TEN  | ⚡ Free |
| 73   | Ricky Pearsall    | SF   | ⚡ Free |
| 81   | Khalil Shakir     | BUF  | ⚡ Free |
| 84   | Jauan Jennings    | MIN  | ⚡ Free |

#### TE

| Rank | Player         | Team | Owner   |
| ---- | -------------- | ---- | ------- |
| 67   | David Njoku    | LAC  | ⚡ Free |
| 87   | T.J. Hockenson | MIN  | ⚡ Free |
| 105  | Evan Engram    | DEN  | ⚡ Free |
| 113  | Jake Ferguson  | DAL  | ⚡ Free |
| 114  | Hunter Henry   | NE   | ⚡ Free |
| 138  | Juwan Johnson  | NO   | 🏆 Team |

#### Flex

| Rank | Player             | Team | Pos | Owner   |
| ---- | ------------------ | ---- | --- | ------- |
| 3    | Bijan Robinson     | ATL  | RB  | 🏆 Team |
| 16   | James Conner       | ARI  | RB  | ⚡ Free |
| 22   | Alvin Kamara       | NO   | RB  | ⚡ Free |
| 23   | Tee Higgins        | CIN  | WR  | 🏆 Team |
| 26   | Amon-Ra St. Brown  | DET  | WR  | 🏆 Team |
| 27   | Kenneth Walker III | KC   | RB  | 🏆 Team |
| 40   | Tyrone Tracy Jr.   | NYG  | RB  | ⚡ Free |
| 44   | Jerry Jeudy        | CLE  | WR  | ⚡ Free |
| 52   | Isiah Pacheco      | DET  | RB  | ⚡ Free |
| 57   | Jerome Ford        | WAS  | RB  | ⚡ Free |
| 63   | Calvin Ridley      | TEN  | WR  | ⚡ Free |
| 67   | David Njoku        | LAC  | TE  | ⚡ Free |
| 68   | J.K. Dobbins       | DEN  | RB  | 🏆 Team |
| 73   | Ricky Pearsall     | SF   | WR  | ⚡ Free |
| 79   | Austin Ekeler      | FA   | RB  | ⚡ Free |
| 138  | Juwan Johnson      | NO   | TE  | 🏆 Team |

#### K

| Rank | Player           | Team | Owner   |
| ---- | ---------------- | ---- | ------- |
| 1    | Wil Lutz         | DEN  | ⚡ Free |
| 2    | Chase McLaughlin | TB   | ⚡ Free |
| 5    | Evan McPherson   | CIN  | ⚡ Free |
| 6    | Jake Elliott     | PHI  | ⚡ Free |
| 10   | Matt Gay         | LV   | ⚡ Free |

#### D/ST

| Rank | Player                     | Team | Owner   |
| ---- | -------------------------- | ---- | ------- |
| 2    | Arizona Cardinals D/ST     | ARI  | ⚡ Free |
| 3    | Eagles D/ST                | PHI  | 🏆 Team |
| 5    | Minnesotaikings D/St D/ST  | MIN  | ⚡ Free |
| 6    | Washington Commanders D/ST | WAS  | ⚡ Free |
| 8    | San Francisco 49ers D/ST   | SF   | ⚡ Free |
| 9    | Cincinnati Bengals D/ST    | CIN  | ⚡ Free |

### Unranked Players on Roster

| Player             | Team | Position | Points |
| ------------------ | ---- | -------- | ------ |
| Jonathon Brooks    | CAR  | RB       | 0.0    |
| Emmett Johnson     | KC   | RB       | 0.0    |
| Roschon Johnson    | CHI  | RB       | 0.0    |
| KC Concepcion      | CLE  | WR       | 0.0    |
| Christian Watson   | GB   | WR       | 0.0    |
| De'Zhaun Stribling | SF   | WR       | 0.0    |
| Jordyn Tyson       | NO   | WR       | 0.0    |
| Eddy Pineiro       | SF   | K        | 0.0    |

## Sample Output - ros-analysis.md

### Top 10 Available Players + Bottom 10 Team Players

## My League The Sheriff

### 🎯 Top 10 Available Players

| Rank | Player             | Position | Team |
| ---- | ------------------ | -------- | ---- |
| 85   | De'Zhaun Stribling | WR       | SF   |
| 89   | Xavier Worthy      | WR       | KC   |
| 91   | Wan'Dale Robinson  | WR       | TEN  |
| 93   | Matthew Golden     | WR       | GB   |
| 97   | Rachaad White      | RB       | WAS  |
| 100  | Keaton Mitchell    | RB       | LAC  |
| 111  | Jordyn Tyson       | WR       | NO   |
| 112  | Keenan Allen       | WR       | IND  |
| 114  | Juwan Johnson      | TE       | NO   |
| 115  | Jonah Coleman      | RB       | DEN  |

### 📉 Bottom 10 - The Sheriff

| Rank | Player          | Position | Team |
| ---- | --------------- | -------- | ---- |
| NR   | Ja'Kobi Lane    | WR       | BAL  |
| NR   | Chargers        | DEF      | LAC  |
| NR   | Jason Myers     | K        | SEA  |
| 136  | Malik Willis    | QB       | MIA  |
| 120  | Patrick Mahomes | QB       | KC   |
| 99   | Makai Lemon     | WR       | PHI  |
| 86   | KC Concepcion   | WR       | CLE  |
| 77   | Tucker Kraft    | TE       | GB   |
| 75   | Jalen Hurts     | QB       | PHI  |
| 65   | MarShawn Lloyd  | RB       | GB   |

_167 players owned in this league_
