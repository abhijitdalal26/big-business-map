# Automatic data updates

`python pipeline/update.py` refreshes the parts of the site that come from stable, official
sources, checks the new data, and only then replaces the old data. A Windows task runs it every
Sunday at 10:00 (`pipeline/schedule_windows.ps1`). The result of the last run is in
`logs/latest.md`.

## What updates automatically

| Data | Source | Feeds |
|---|---|---|
| 27 stock indexes, monthly | Yahoo Finance | Stock markets: performance, ranking, correlation |
| Exchange rates, monthly | US Federal Reserve and OECD (via FRED); Yahoo for the Argentine peso | US-dollar views |
| Market value by country, yearly | World Bank / World Federation of Exchanges | Market-size chart |
| Population and GDP | World Bank | Unicorns per person / per $ of GDP |

## What stays manual, and why

| Data | Why not automatic |
|---|---|
| CB Insights unicorn board | Scraped from a web page whose layout changes; a silent break would show wrong numbers |
| companiesmarketcap.com listings (exchanges, listed universe) | Scraped, estimate-grade, takes hours |
| Forbes Global 2000, Fortune Global 500 | Published once a year |
| Hurun cross-check, curated notes | Need a person to read them |

## Checks before anything is replaced

1. No file loses more than 2% of its rows, and no index disappears.
2. 12 index closes for December 2024 must equal the official closes, and 10 exchange rates must be within 1% of official values.
3. History must not be rewritten: fewer than 1% of index values older than 3 months may move by more than 0.5%.
4. The latest month cannot go backwards; indexes with no data for 2 months are flagged.
5. The World Bank world total for 2024 must stay within 3%, and no more than 5% of economies may be lost.
6. After the rebuild the site data must load, with 27 indexes and 90+ economies.

If any check fails, the site keeps the previous data and the log explains why. The previous
files are backed up to `backup/<date>/` (the 5 newest are kept). The build also removes bad points
on its own (exchange-rate glitches and World Bank reporting errors) and lists them on the page.

The update changes files on this computer only. To publish, commit and push as usual.

## Running on GitHub (no PC needed)

`.github/workflows/update-data.yml` runs `pipeline/update.py` on GitHub every Sunday at 04:30 UTC
and commits the new data if anything changed. Start it by hand from the repo's **Actions** tab
("Weekly data update" → "Run workflow"). Each run's report is attached to the run as `update-report`.
