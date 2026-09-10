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

Create a file named `config.json` in the root. It must be valid JSON containing a `leagues` array; separate multiple leagues with a comma. Each league is validated when loaded, and invalid entries are skipped with a warning.

```json
{
  "leagues": [
    {
      "platform": "espn",
      "league_id": "123456",
      "team_name": "My Team",
      "scoring_type": "half",
      "league_name": "My League",
      "lineup_slots": {}
    }
  ]
}
```

**Required fields:**

- `platform`: One of `"espn"`, `"sleeper"`, or `"yahoo"`
- `league_id`: String containing your league's ID (found in the league's website URL)
- `team_name`: Your exact team name as it appears in the league

**Optional fields:**

- `scoring_type`: Either `"half"` (half-PPR) or `"full"` (full-PPR). For ESPN and Sleeper leagues, this is auto-detected from the league settings if omitted; for Yahoo! leagues, defaults to `"half"` if not specified.
- `league_name`: Display name for the league in reports. Auto-detected from ESPN and Sleeper if omitted.
- `lineup_slots`: Object mapping positions to starter counts (see below). Auto-detected from ESPN/Sleeper settings if omitted; required for Yahoo! leagues.

**Auto-Detection Details:**
For ESPN and Sleeper leagues, if you don't specify `scoring_type`, `league_name`, or `lineup_slots`, they are automatically pulled from the league's API. This means you can often provide just the three required fields, and everything else will be filled in. Yahoo! has no public API, so these fields must be set explicitly for Yahoo! leagues.

### Configuring `lineup_slots` for Yahoo! leagues

Since Yahoo! has no public API, `lineup_slots` must be set manually in `config.json` for Yahoo! leagues (ESPN and Sleeper leagues auto-detect it and don't need this). The value is an object mapping each position to how many starters your league uses at that slot:

| Key         | Meaning                                    |
| ----------- | ------------------------------------------ |
| `QB`        | Quarterback                                |
| `RB`        | Running back                               |
| `WR`        | Wide receiver                              |
| `TE`        | Tight end                                  |
| `FLEX`      | RB/WR/TE flex (Yahoo!'s "W/R/T")           |
| `SUPERFLEX` | QB/RB/WR/TE superflex (Yahoo!'s "Q/W/R/T") |
| `D/ST`      | Team defense/special teams                 |
| `K`         | Kicker                                     |

Omit a key (or set it to `0`) if your league doesn't start that position - the weekly report will still include a row for it noting it isn't part of your starting lineup, except for unused kicker and defense rows, which are hidden. For example, a Yahoo! league that starts 1 QB, 2 RB, 2 WR, 1 TE, 2 FLEX ("W/R/T"), 1 SUPERFLEX ("Q/W/R/T"), 1 K, and 1 D/ST would use:

```json
"lineup_slots": {
  "QB": 1,
  "RB": 2,
  "WR": 2,
  "TE": 1,
  "FLEX": 2,
  "SUPERFLEX": 1,
  "K": 1,
  "D/ST": 1
}
```

Create a `.env` file in the root:

```text
RANKINGS_URL=https://some-website.com?week={week}&export=csv
REST_OF_SEASON_RANKINGS_PATTERN=Your Pattern*.csv

# Only required for private ESPN leagues
ESPN_SWID={your-espn-swid}
ESPN_S2=your-espn-s2-value
```

- `RANKINGS_URL`: Set this to your rankings source that supports weekly exports as CSV. The `{week}` placeholder is replaced with the current week number.
- `REST_OF_SEASON_RANKINGS_PATTERN`: Optional glob pattern for finding rest-of-season rankings files in your Downloads folder. If set, the pipeline copies matching files to `rankings/rest-of-season.csv`. Omit if you prefer to manually maintain this file.
- `ESPN_SWID` / `ESPN_S2`: Only needed if any configured league is a private ESPN league. Log in to ESPN in your browser, open dev tools, and copy the `espn_s2` and `SWID` cookie values (`SWID` includes the surrounding curly braces).

If `RANKINGS_URL` is not set, the download step will not attempt to refresh files in `rankings/`. Instead, it prints how old each existing file is so you know whether they need to be replaced manually.

## Adding your own rankings

You can use rankings from any source as long as you save them as CSV files in the `rankings/` directory. The weekly lineup report looks for these exact file names:

| File            | Players                             |
| --------------- | ----------------------------------- |
| `qb.csv`        | Quarterbacks                        |
| `half_flex.csv` | RB, WR, and TE for half-PPR leagues |
| `ppr_flex.csv`  | RB, WR, and TE for full-PPR leagues |
| `kicker.csv`    | Kickers                             |
| `dst.csv`       | Team defenses                       |

Each weekly file must have this exact header row and these columns: `Rank,Player Name,Team,Position`. For example:

```csv
Rank,Player Name,Team,Position
1,Josh Allen,BUF,QB
```

The full-PPR league setting uses `ppr_flex.csv`; the half-PPR setting uses `half_flex.csv`. The position values in the flex file should be `RB`, `WR`, or `TE`, and the defense file should use `DST` for its position.

The rest-of-season report uses a separate file named `rest-of-season.csv`. It must have the header `Player,Position,Team,Rank`.

**Automatic updates:** If you set `REST_OF_SEASON_RANKINGS_PATTERN` in `.env`, the pipeline automatically copies matching files from your Downloads folder to `rankings/rest-of-season.csv`.

**Manual maintenance:** If you prefer to maintain this file manually, place it in `rankings/rest-of-season.csv` and either set `REST_OF_SEASON_RANKINGS_PATTERN` to an empty string or skip the full `uv run fantasy-ranks` command and run the relevant modules individually.

## Generating lineups

```shell
uv run fantasy-ranks
```

This runs the full pipeline:

1. Downloads the latest weekly rankings (if `RANKINGS_URL` is set)
2. Pulls rosters from ESPN and Sleeper leagues
3. Fetches and applies the latest transactions for any configured Yahoo! leagues (requires `YAHOO_COOKIE`, and only if the league's roster JSON has already been created via one of the import options below)
4. Generates a weekly start/sit report: `lineups/start-sit.md`
5. Refreshes rest-of-season rankings (if `REST_OF_SEASON_RANKINGS_PATTERN` is set)
6. Identifies top available players by position

**Output Files:**

- **`lineups/start-sit.md`** — Weekly analysis with starting roster recommendations, bench breakdowns, top 5 available players by position, and actions for every starting spot in each league.
- **`lineups/ros-analysis.md`** — Rest-of-season analysis showing top available players, bottom-ranked rostered players, and actions for every starting spot in each league.

For each team, the report includes:

- A **Starting Roster** table listing each starting slot (based on `lineup_slots`), the current starter and their position rank, the best available free agent at that slot and their rank, and an evaluation (`Optimal`, `+N Ranks Better`, `Unranked`, etc.). Positions configured with 0 starters still get a row noting they aren't part of your starting lineup, and a `SUPERFLEX` row/section appears only for leagues that use one.
- A **Bench** table listing the rest of the team's rostered players (those not filling a starting, FLEX, or SUPERFLEX slot) and their current position rank.
- A **Top 5 Available Players by Position** section listing the best free agents at QB, RB, WR, TE, FLEX, D-ST, and K (plus SUPERFLEX for leagues that use it).

## Importing Yahoo! rosters

Yahoo! leagues are kept up to date manually. There are two ways to import or refresh a Yahoo! draft roster:

### Option 1: Fetch automatically

Yahoo!'s draft results page requires an authenticated session, so you need to supply a session cookie once:

1. Log into Yahoo! Fantasy Football in your browser.
2. Open developer tools, go to the Console tab, run `copy(document.cookie)`, then paste the copied value. If requests still fail (e.g. redirected to login), instead copy the full `Cookie` request header from the Network tab (use the "raw" headers view) or read the cookie list from the Application/Storage tab for `football.fantasysports.yahoo.com`.
3. Add it to your `.env` file: `YAHOO_COOKIE=<paste cookie value here>`.

Then run:

```shell
uv run python -m fantasy_ranks.fetch_yahoo_draft {leagueId}
```

This downloads the draft results page (sorted by team), saves the extracted text to `rosters/yahoo_{leagueId}.txt`, and automatically runs the parser to produce `rosters/yahoo_{leagueId}_owned_players.json`.

### Option 2: Copy/paste manually

Open the draft results page, copy the entire page (press `Ctrl + A`, then `Ctrl + C`), and save the copied text to:

```text
rosters/yahoo_{leagueId}.txt
```

Then run the parser with your league ID:

```shell
uv run python src\fantasy_ranks\parse_yahoo_draft.py {leagueId}
```

The generated `rosters/yahoo_{leagueId}_owned_players.json` file is treated as the source of truth. The main `fantasy-ranks` command does not run the Yahoo! parser automatically.

### Updating Yahoo! rosters after waivers

Yahoo! roster updates run automatically as part of `uv run fantasy-ranks` for any league configured with `"platform": "yahoo"` in `config.json` (requires `YAHOO_COOKIE` to be set). If `rosters/yahoo_{leagueId}_owned_players.json` doesn't exist yet, the draft is imported automatically first. You can also run it for a single league on demand:

```shell
uv run python -m fantasy_ranks.fetch_yahoo_transactions {leagueId}
```

This downloads the transactions page, saves the extracted text to `rosters/yahoo_updates_{leagueId}.txt`, and applies it to `rosters/yahoo_{leagueId}_owned_players.json`. Reprocessing transactions is safe: players are not added if they are already on the roster, and dropping a player who has already been removed has no additional effect.

If you'd rather update rosters manually instead, open the Yahoo! transactions page, copy the entire page (press `Ctrl + A`, then `Ctrl + C`), and save the copied text to:

```text
rosters/yahoo_updates_{leagueId}.txt
```

Then update the local roster file by running:

```shell
uv run python src\fantasy_ranks\update_yahoo_rosters.py {leagueId}
```

## Resetting the project

To clear out generated data (`rankings/`, `rosters/`, and `lineups/` directories) and start fresh:

```shell
uv run python -m fantasy_ranks.reset_project
```

## Running tests

```shell
uv run pytest
```

## Troubleshooting

### Rankings files missing or old

- Check that `RANKINGS_URL` is set in `.env`
- Verify the URL is still valid and returns CSV format
- If you see "RANKINGS_URL not set" — the download step skips automatically; place CSV files manually in `rankings/` or update `.env`

### Config validation warnings

- Invalid league entries are skipped with a warning message printed to the console
- Check your `config.json` for malformed JSON (tools like VSCode's JSON validator can help)
- Verify all required fields (`platform`, `league_id`, `team_name`) are present and correctly formatted

### ESPN/Sleeper API failures

- If you see "401 Unauthorized" errors: your ESPN credentials (`ESPN_SWID` / `ESPN_S2`) may be expired; re-copy them from your browser
- If public ESPN/Sleeper leagues fail: verify the `league_id` is correct and matches the league's public URL
- Check your internet connection; the pipeline makes external API calls

### Yahoo roster parsing issues

- Make sure you've copied the **entire draft results page sort by team** or **transactions page** (Ctrl+A, Ctrl+C) before pasting into the file
- Save the file to exactly `rosters/yahoo_{leagueId}.txt` or `rosters/yahoo_updates_{leagueId}.txt`
- Run the parser command with the correct league ID matching your config

### Missing output files

- `start-sit.md` is created only if at least one league loads successfully
- `ros-analysis.md` is created only if `rest-of-season.csv` exists and contains valid rankings
- Check the console output for error messages indicating which step failed

## Project structure

- `src/fantasy_ranks/` — the installable package with the following runnable modules:

  | Module                        | Purpose                                                                                                                           |
  | ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
  | `cli.py`                      | Orchestrates the full pipeline (called by `uv run fantasy-ranks`)                                                                 |
  | `download_weekly_rankings.py` | Downloads rankings from `RANKINGS_URL` for the current week                                                                       |
  | `espn_rosters.py`             | Fetches rosters for all configured ESPN leagues                                                                                   |
  | `sleeper_rosters.py`          | Fetches rosters for all configured Sleeper leagues                                                                                |
  | `output_rankings.py`          | Generates the weekly start/sit report (`start-sit.md`)                                                                            |
  | `copy_newest_ros.py`          | Copies matching rest-of-season rankings to `rankings/rest-of-season.csv`                                                          |
  | `find_top_available.py`       | Identifies top available free agents by position                                                                                  |
  | `fetch_yahoo_draft.py`        | Downloads and parses a Yahoo! draft results page into a roster file (run with league ID: `uv run python -m fantasy_ranks.fetch_yahoo_draft 960067`) |
  | `parse_yahoo_draft.py`        | Parses Yahoo! draft results into a roster file (run with league ID: `uv run python -m fantasy_ranks.parse_yahoo_draft 960067`)    |
  | `fetch_yahoo_transactions.py` | Downloads and applies a Yahoo! transactions page to a roster file; runs automatically for Yahoo! leagues as part of `uv run fantasy-ranks` (run standalone with league ID: `uv run python -m fantasy_ranks.fetch_yahoo_transactions 960067`) |
  | `update_yahoo_rosters.py`     | Updates Yahoo! roster with transaction changes (run with league ID: `uv run python -m fantasy_ranks.update_yahoo_rosters 960067`) |
  | `yahoo_web.py`                | Shared helpers for fetching Yahoo! pages and extracting their plain text (not run directly)                                       |
  | `reset_project.py`            | Clears all generated data (`rankings/`, `rosters/`, `lineups/`)                                                                   |

  Any module can be run standalone via `uv run python -m fantasy_ranks.<module>` plus any required arguments.

- `tests/` — mirrors the package modules, with shared fixtures for mocking ESPN/Sleeper API calls in `tests/conftest.py`.

## Sample Output - start-sit.md

### League of Dreams The Sheriff — Starting Roster

| Slot | Starter                  | Current Rank   | Best Available Free Agent            | FA Rank        | Evaluation          |
| ---- | ------------------------ | -------------- | ------------------------------------ | -------------- | ------------------- |
| QB   | Jalen Hurts (QB)         | QB5            | Daniel Jones (QB - IND)              | QB24           | Optimal             |
| QB   | Malik Willis (QB)        | QB18           | Daniel Jones (QB - IND)              | QB24           | Optimal             |
| RB   | Christian McCaffrey (RB) | RB2            | Aaron Jones Sr. (RB - MIN)           | RB37           | Optimal             |
| RB   | Breece Hall (RB)         | RB15           | Aaron Jones Sr. (RB - MIN)           | RB37           | Optimal             |
| WR   | Jaxon Smith-Njigba (WR)  | WR4            | Wan'Dale Robinson (WR - TEN)         | WR40           | Optimal             |
| WR   | Chris Olave (WR)         | WR7            | Wan'Dale Robinson (WR - TEN)         | WR40           | Optimal             |
| WR   | Luther Burden III (WR)   | WR24           | Wan'Dale Robinson (WR - TEN)         | WR40           | Optimal             |
| TE   | Tucker Kraft (TE)        | TE5            | Juwan Johnson (TE - NO)              | TE10           | Optimal             |
| K    | Jason Myers (K)          | K7             | Evan McPherson (K - CIN)             | K4             | +3 Ranks Better     |
| D/ST | — (Empty Slot)           | —              | Pittsburgh Steelers D/ST (DST - PIT) | DST3           | Fill via Free Agent |
| FLEX | Ashton Jeanty (RB)       | RB17 / FLEX 29 | Wan'Dale Robinson (WR - TEN)         | WR40 / FLEX 80 | Optimal             |
| FLEX | Bhayshul Tuten (RB)      | RB27 / FLEX 54 | Wan'Dale Robinson (WR - TEN)         | WR40 / FLEX 80 | Optimal             |

### Bench

| Player              | Current Rank    |
| ------------------- | --------------- |
| Terry McLaurin (WR) | WR27 / FLEX 57  |
| MarShawn Lloyd (RB) | RB28 / FLEX 61  |
| KC Concepcion (WR)  | WR47 / FLEX 99  |
| Makai Lemon (WR)    | WR56 / FLEX 116 |
| Ja'Kobi Lane (WR)   | WR75 / FLEX 151 |

### Top 5 Available Players by Position

#### Quarterbacks (QB)

| Player                     | Rank |
| -------------------------- | ---- |
| Daniel Jones (QB - IND)    | QB24 |
| C.J. Stroud (QB - HOU)     | QB25 |
| Aaron Rodgers (QB - PIT)   | QB26 |
| Kirk Cousins (QB - LV)     | QB27 |
| Jacoby Brissett (QB - ARI) | QB28 |

#### Running Backs (RB)

| Player                        | Rank |
| ----------------------------- | ---- |
| Aaron Jones Sr. (RB - MIN)    | RB37 |
| Rachaad White (RB - WAS)      | RB38 |
| Tyler Allgeier (RB - ARI)     | RB40 |
| Mike Washington Jr. (RB - LV) | RB41 |
| Woody Marks (RB - HOU)        | RB43 |

#### Wide Receivers (WR)

| Player                       | Rank |
| ---------------------------- | ---- |
| Wan'Dale Robinson (WR - TEN) | WR40 |
| Jalen Coker (WR - CAR)       | WR44 |
| Jakobi Meyers (WR - JAC)     | WR45 |
| Matthew Golden (WR - GB)     | WR49 |
| Khalil Shakir (WR - BUF)     | WR50 |

#### Tight Ends (TE)

| Player                     | Rank |
| -------------------------- | ---- |
| Juwan Johnson (TE - NO)    | TE10 |
| Dalton Schultz (TE - HOU)  | TE16 |
| Hunter Henry (TE - NE)     | TE17 |
| Brenton Strange (TE - JAC) | TE18 |
| T.J. Hockenson (TE - MIN)  | TE20 |

#### Flex (RB/WR/TE)

| Player                       | Rank           |
| ---------------------------- | -------------- |
| Wan'Dale Robinson (WR - TEN) | WR40 / FLEX 80 |
| Juwan Johnson (TE - NO)      | TE10 / FLEX 85 |
| Jalen Coker (WR - CAR)       | WR44 / FLEX 89 |
| Jakobi Meyers (WR - JAC)     | WR45 / FLEX 90 |
| Aaron Jones Sr. (RB - MIN)   | RB37 / FLEX 94 |

#### Defense (D/ST)

| Player                                | Rank  |
| ------------------------------------- | ----- |
| Pittsburgh Steelers D/ST (DST - PIT)  | DST3  |
| Dallas Cowboys D/ST (DST - DAL)       | DST8  |
| Minnesotaikings D/St D/ST (DST - MIN) | DST10 |
| Baltimore Ravens D/ST (DST - BAL)     | DST11 |
| Buffalo Bills D/ST (DST - BUF)        | DST12 |

#### Kickers (K)

| Player                    | Rank |
| ------------------------- | ---- |
| Evan McPherson (K - CIN)  | K4   |
| Chase McLaughlin (K - TB) | K8   |
| Chris Boswell (K - PIT)   | K9   |
| Tyler Loop (K - BAL)      | K10  |
| Cairo Santos (K - CHI)    | K11  |

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

167 players owned in this league
