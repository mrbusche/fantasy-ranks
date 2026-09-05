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
      "platform": "", # required: "espn" or "sleeper"
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
uv run python main.py
```

This downloads the latest weekly rankings, pulls your rosters from ESPN/Sleeper, and writes the resulting analysis to `lineups/start-sit.md`.

## Running tests

```shell
uv run pytest
```
