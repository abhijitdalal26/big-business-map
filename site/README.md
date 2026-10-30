# Earth Economy: interactive research site

Open `index.html` in a browser. No server is needed, but you do need internet for the chart library and fonts.

| Page | What it answers |
|---|---|
| `index.html` | Headline numbers, teaser charts, sources and methodology |
| `context.html` | The big picture: ~400M firms, informal economy, VC, IPOs, M&A, trillion-dollar club, sovereign funds, co-ops |
| `scale.html` | How big the giants are: top 100, size distribution, concentration, company vs country |
| `geography.html` | World map, country rankings, revenue share vs GDP share, India deep-dive |
| `sectors.html` | What business does: sector treemap, margins, valuations, oligopolies |
| `ownership.html` | State, family, private and co-op giants that are not on stock markets |
| `markets.html` | 60 exchanges, market cap vs GDP, trillion-dollar club, exchange drilldown, each country's index and market size over time |
| `startups.html` | 1,440 unicorns in all 55 countries, per-person and per-GDP ranking, investors, AI labs, India panel |
| `time.html` | A decade of change: cohort growth, rank mobility, profit-pool migration |
| `directory.html` | Search and filter ~15,000 companies, with CSV export |
| `notebook.html` | **Every quotable fact, caveat and story angle in one searchable page** |

Rebuild a page's data with `python site/build/<page>.py`. Market history and unicorn density: run `python stock_market/scripts/fetch_history.py`, then `python site/build/market_history.py` and `python site/build/unicorn_density.py`. After editing `site/notes/*.md`, run `python site/build/notebook.py`.
Sourced context tables (VC, IPOs, informality, etc.) are in `site/build/context_data/*.csv`.

## Verify before quoting
- SpaceX shows as listed (~$1.9T) in the Oct 2026 market-cap data, after the Feb 2026 merger with xAI. Confirm this.
- 2026 AI valuations (Anthropic $965B, OpenAI $852B, Stripe $159B) come from press reports.
- The state-ownership labels on the ownership page are curated by hand, so spot-check them.
- World Bank listed-company counts have breaks (India 2019/2020, China 2019, India 2025). Use world and US figures for trends.
- Trillion-dollar dates for Eli Lilly and Samsung are uncited on Wikipedia.
- VC totals differ by tracker: PitchBook/KPMG $512B vs Crunchbase ~$430B for 2025.
