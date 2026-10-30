# Earth Economy — data pack for a Substack piece

A four-layer dataset of what business exists on earth, how big it is, and where the
visible numbers stop. Every layer keeps its own source and methodology; they are
never silently mixed.

| Layer | Source | What it gives |
|---|---|---|
| Public giants | Forbes Global 2000 (2025) | 2,000 listed companies, full financials, 10-year history |
| Invisible giants | Fortune Global 500 (2025) | 90 state-owned, private and mutual companies absent from Forbes |
| Venture layer | Forbes Cloud 100 + Next Billion-Dollar Startups (2025) | 125 private, VC-backed companies |
| The frame | World Bank Open Data | $111.7T world GDP, 3.7B workers, 48k listed companies, sector split |

## Files

| Path | What it is |
|---|---|
| `data/global2000_2025.csv` | 2,000 public companies, 29 columns + sector taxonomy |
| `data/global2000_2025_history.csv` | Long format, 10-year revenue/profit/assets/headcount |
| `data/fortune_g500_2025.csv` | 500 Fortune Global 500 companies, scraped from company pages |
| `data/fortune_labels.csv` | Manual ownership labels for the 104 Fortune names outside Forbes |
| `data/companies_master.csv` | All company sources stacked, with `source` and `ownership` |
| `data/startups_2025.csv` | Cloud 100 + Next Billion-Dollar Startups |
| `data/industry_taxonomy.csv` | 13 sectors, 30 industries, revenue and company counts |
| `data/world_macro.csv` | World Bank indicators 2000-2024 (GDP, sector shares, employment, listed companies) |
| `data/country_gdp_2024.csv` | GDP by country, 2024 |
| `output/global2000_2025.xlsx` | Workbook: Companies, By Country, By Industry, Startups, All sources, Outside Forbes, Notes |
| `output/charts/*.png` | 13 charts at 200 dpi |
| `analysis/findings.md` | Public-layer numbers and caveats |
| `analysis/startups_findings.md` | Venture-layer numbers |
| `analysis/atlas.md` | **The full four-layer narrative, with all headline numbers** |

## Study pack (the analysis to write from)

The `data_analysis/` engine reconciles every source into one company universe
(15,175 companies from 17,985 source rows) and runs eight analysis modules
over it: scale, geography, industry, ownership, capital, private capital, time
series, and data quality. Its output is a study pack — **not** article prose.
It is the place to look up a number, check its caveat, and see the chart.

| Path | What it is |
|---|---|
| `data_analysis/output/index.html` | **Start here** — the browsable study pack: open it in a browser |
| `data_analysis/output/STUDY_PACK.md` | The same pack in Markdown, for reading in a text editor |
| `data_analysis/output/study_pack.html` | A flat single-file dump of the pack (no navigation) |
| `data_analysis/output/README.md` | Index of the pack and how to rebuild it |
| `data_analysis/output/charts/*.png` | 36 charts at 200 dpi, one per question |
| `data_analysis/output/data/*.csv` | 46 full tables behind every chart and claim |
| `data_analysis/output/metrics.json` | Every metric, machine-readable |

The app's last section is a **company directory**: all 15,175 companies in the
reconciled universe, searchable, each with its official website, Wikipedia and
Forbes links where the source files know them.

Rebuild it with:

```
python data_analysis/build_report.py
```

## The headline numbers

- World GDP **$111.7T**; 3.70B workers; **47,980** listed companies.
- The 2,000 public giants: **$52.9T** revenue, **$4.9T** profit, **$91.3T** market value,
  92.6M employees — revenue equal to 47% of world GDP (scale, not value added).
- Financials are the largest sector by revenue (23%), then Consumer & Retail (17%),
  Energy (13%), Technology (9%).
- Top 100 companies hold **35%** of the list's revenue.
- Agriculture is **4% of GDP but 26% of workers** (~965M people).
- **90 large companies worth $6.4T** sit outside the public list: 56 state-owned
  ($4.1T), 16 private ($1.2T), 15 mutuals ($0.9T). State Grid alone is $555B.
- Russia: 2% of world GDP, **zero** companies in the 2025 Forbes list.

## Rebuilding

```powershell
$py = "C:\Users\abhijit\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
& $py scripts/build_dataset.py      # Forbes JSON -> CSVs
& $py scripts/taxonomy.py           # add sector + industry_canon, write taxonomy CSV
& $py scripts/build_startups.py     # Cloud 100 + Next Billion-Dollar
& $py scripts/fetch_fortune500.py   # scrape 500 Fortune company pages (cached)
& $py scripts/label_fortune.py      # curated ownership labels
& $py scripts/build_master.py       # merge all company sources
& $py scripts/fetch_macro.py        # World Bank macro data
& $py scripts/analyze.py            # -> analysis/findings.md
& $py scripts/make_charts.py        # -> charts 01-08
& $py scripts/make_atlas_charts.py  # -> charts 09-13
& $py scripts/export_excel.py       # -> workbook
```

Raw sources are cached in `data/raw/` (Forbes JSON, Fortune HTML pages, Fortune list).

## Rules that keep this honest

1. **Never sum across layers inside one chart.** Forbes and Fortune use different
   fiscal years and definitions; Cloud 100 is valuation, not revenue.
2. **Revenue is not value added.** "Combined revenue equals 47% of world GDP" is
   defensible; "these companies are 47% of the economy" is not.
3. **Forbes' market values are May 2025 snapshots.**
4. **Forbes' industry labels are free text** (39 variants, e.g. "Banking" and
   "Banking and Financial Services"). Always use `sector` / `industry_canon`.
5. **Fortune's "Company type" mislabels state firms as "Private"** — use our
   `ownership` column, curated in `scripts/label_fortune.py`.
6. **Hong Kong and Taiwan are separate from China** in Forbes' country field.

## What is still not covered

- **Small business and the informal economy.** The bottom ~95% of firms by count is
  invisible in every company list; the World Bank/ILO aggregates are the only handle.
- **Co-operatives and mutuals outside the Fortune 500** (Rabobank, Migros and 13 others
  are captured; most are not).
- **Per-exchange listings** (NSE/BSE, LSE, TSE...) — a pipeline per exchange.
- **Ownership networks** (who owns whom) — would need Orbis/BvD or SEC 13F data.
