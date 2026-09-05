# Fantasy Ranks

Generate lineups for your Sleeper and ESPN leagues

## Setup

Create a file named config.json in the root, separate multiple leagues with a comma, valid json is required

```json
{
  "leagues": [
    {
      "platform": "", # espn or sleeper
      "league_id": "", # get this from the website URL
      "scoring_type": "", # half or ppr
      "team_name": "", # your exact team name in the league
      "league_name": "" # not required but will help differentiate leagues
    }
  ]
}
```

Create a `.env` file

```text
RANKINGS_URL=https://some-website.com?week={week}&export=csv
```

If you found this website you can figure out how your favorite rankings site exposes their rankings, you will want this exported as csv

## Generating lineups

```shell
uv run python main.py
```
