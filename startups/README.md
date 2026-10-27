# Startups — the global unicorn layer

Separate from the atlas (`data/`, `output/`), the listed universe
(`listed_universe/`) and the exchange view (`stock_market/`).

Question it answers: **who are the large private, venture-backed companies on earth,
where are they, and what are they worth on paper?**

## Sources

| Source | Companies | What it gives |
|---|---|---|
| CB Insights Unicorn Board (public page) | **1,442** | Valuation, country, city, industry, investors, date joined |
| Forbes Cloud 100 + Next Billion-Dollar (2025) | 125 | Editorial list, funding, employees |
| Merged, deduped | **1,479** | one table |

The two Forbes lists match 125 of the CB entries; 37 Forbes companies were not on
the CB board and were appended, so the merged table is slightly larger than either.

## Headline numbers

- **1,442 unicorns**, combined **$7.35 trillion** of paper valuation.
- **55 countries**: US 862 ($5.14T) · China 170 ($1.0T) · UK 73 ($279B) · India 63 ($144B).
- Top of the board: **Anthropic $965B · OpenAI $840B · ByteDance $480B ·
  Databricks $190B · Stripe $159B**.
- Industry: Enterprise Tech dominates (560 companies), then Financial Services (227),
  Industrials (226), Consumer & Retail (206), Healthcare (125).

## Files

| Path | What it is |
|---|---|
| `data/unicorns_cbinsights.csv` | raw board: 1,442 rows with valuation, investors, date joined |
| `data/startups_global.csv` | merged/deduped: 1,479 companies |
| `charts/st01_top_unicorns.png` | top 20 by valuation |
| `charts/st02_countries.png` | unicorns by country |
| `charts/st03_industries.png` | valuation by sector |

## Caveats — these matter more than usual

1. **Valuations are private marks, not prices.** They are the last funding round,
   sometimes years old. A company can be marked at $10B and be worth less today.
2. **The board lags reality.** Companies that IPO'd, were acquired or collapsed may
   still appear. Treat the list as "companies that reached $1B on paper", not "current
   unicorns".
3. **The order is not a ranking of quality or size.** CB's Anthropic ($965B) > OpenAI
   ($840B) ordering is a source figure — verify against primary reporting before you
   publish it. Forbes' 2025 Cloud 100 had OpenAI at $300B, which shows how fast and how
   inconsistently these marks move.
4. **Unicorns are not "all startups".** This is the $1B+ private, VC-backed tail. Seed
   and early-stage companies, bootstrapped firms and state-backed ventures are elsewhere
   (or nowhere).
5. **Do not add this to the public companies' market value.** Private marks and traded
   prices are not the same kind of number.

## Rebuild

```powershell
$py = "C:\Users\abhijit\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
& $py startups/scripts/build_startups.py
& $py startups/scripts/make_charts.py
```
