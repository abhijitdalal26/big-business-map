# Listed universe — a separate, larger dataset

This folder is **deliberately separate** from the atlas in the parent directory
(`data/`, `analysis/`, `output/`). Nothing here overwrites or merges into the
Forbes/Fortune/World Bank layer. Different sources, different trust levels, no
silent mixing.

## Why it exists

The atlas answers "what kinds of big business exist". This folder answers a
different question: "how many listed companies can we actually see, with a
revenue figure attached". It is a coverage experiment, not a curated list.

## Sources and trust

| Source | Rows | Trust | What it gives |
|---|---|---|---|
| SEC XBRL frames (us-gaap) | 5,500 | **Authoritative** — audited filings | Revenue (USD), CIK, fiscal period, 7 revenue concepts |
| companiesmarketcap.com | 10,100 | **Estimate-grade** — aggregated, unaudited | Market cap, country, TTM revenue |
| Merged universe | 12,525 | mixed, every row labelled | one table with provenance |

The merge rule: when both sources describe the same company, **SEC wins** and the
row is marked `authoritative`. CMC revenue is used only where SEC has nothing, and
is marked `estimate`. Nothing is averaged.

## Numbers (current build)

- **12,512** distinct listed companies in the universe
- **12,087** carry a revenue figure
- **5,190** above $1B revenue; **1,308** above $10B; **87** above $100B
- SEC↔CMC match: 3,090 of 5,500 US filers (matched on ticker first, then exact
  normalised name — never fuzzy, which produced false pairings like HSBC → HSBC USA)
- 5 CMC revenue values were **rejected as implausible** (e.g. Severstal listed at
  $874B, roughly 100× its real revenue)

## Files

| Path | What it is |
|---|---|
| `data/sec_us_revenue.csv` | US filers, 7 XBRL revenue concepts, CY2025 then CY2024 fallback |
| `data/sec_cik_ticker.csv` | SEC CIK → ticker map, used for unambiguous matching |
| `data/cmc_list.csv` | 10,100 companies by market cap: rank, name, slug, ticker, market cap, country |
| `data/cmc_revenue.csv` | TTM revenue per CMC company (scraped from `/revenue/` pages) |
| `data/listed_universe.csv` | **The merged table** — company, country, market cap, revenue, source, confidence, CIK |
| `data/wiki_descriptions.csv` | Wikipedia intro per company (query, title, extract, match) |
| `data/company_profiles.csv` | **company + revenue + market cap + 'what it does' text** |
| `charts/u01_revenue_bands.png` | How many companies are actually big |
| `charts/u02_country_big.png` | $1B+ companies by country (**coverage-biased, read with care**) |

## Build

```powershell
$py = "C:\Users\abhijit\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
& $py listed_universe/scripts/fetch_sec_frames.py          # SEC -> sec_us_revenue.csv
& $py listed_universe/scripts/scrape_cmc.py --pages 101    # CMC list -> cmc_list.csv
& $py listed_universe/scripts/scrape_cmc.py --resume-list --revenue 10100   # TTM revenue
& $py listed_universe/scripts/build_universe.py            # merge -> listed_universe.csv
& $py listed_universe/scripts/make_charts.py
```

All scripts resolve paths relative to their own location, so they can be run from
any working directory.

## Text: what each company does

`data/company_profiles.csv` carries a description for every company it can find:

| Revenue band | With description |
|---|---|
| Over $100B | 100% |
| $20-100B | 95% |
| $5-20B | 92% |
| $1-5B | 76% |
| Under $1B | 48% |

Two sources, labelled in `description_source`:
- **Forbes** (755) — editorial, copyrighted. Read it, then write your own sentence.
- **Wikipedia** (7,061) — CC BY-SA. Quote with attribution.

Missing rows are mostly small caps and name variants (Itōchū, PDD Holdings,
Walmex) where the Wikipedia search could not confirm a match.

## Hard limits — read before quoting a number

1. **The US is complete; the world is not.** SEC figures are audited and cover every
   US filer that reported a revenue concept. Non-US figures are estimates from a
   market-cap-ranked list, so a company with large revenue but a small market cap
   (traders, construction, low-margin industrials) may be missing entirely.
2. **Country counts reflect coverage, not reality.** China shows 266 and the UK 42;
   both are undercounts. Do not put that chart next to a "where business happens" claim.
3. **Revenue periods differ.** SEC is calendar-year 2025 filings; CMC is TTM as of the
   scrape (Oct 2026). Comparing the two within one chart means comparing different
   periods — label it.
4. **3,788 is a floor, not a census.** The true number of companies with $1B+ revenue
   is probably 2–3× that; reaching it requires exchange-level filings from 60+ markets.
5. **A few accented names are garbled** (`Nestl�` for Nestlé) because the source
   serves mixed encodings; the figures are unaffected, the display name is.
6. **No private companies here.** See the parent atlas for Forbes' private 200 and the
   Fortune state-owned layer.

## What would move the needle

- Per-exchange filings for the 20 largest non-US markets (Japan, China, UK, Germany,
  India, Canada, Australia, Korea, France, Switzerland...).
- A paid fundamentals feed (EODHD/FMP) for global tickers — cheap tiers exist but
  coverage below $1B market cap is still thin.
- SEC 20-F filers are already captured via XBRL; non-XBRL foreign issuers are not.
