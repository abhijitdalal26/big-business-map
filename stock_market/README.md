# Stock markets — top companies per exchange

Third dataset, kept separate from the atlas (`data/`, `output/`) and from the
listed universe (`listed_universe/`).

Question it answers: **for every stock exchange we can identify, who are the largest
listed companies, and how big is that market?**

## Method

1. Start from `listed_universe/data/cmc_list.csv` — 10,100 companies with ticker,
   market cap and country.
2. **Non-US tickers** carry an exchange suffix (`.T` Tokyo, `.NS` NSE India, `.L` London,
   `.PA` Euronext Paris, `.SR` Tadawul, `.KS` Korea...). Mapped via
   `data/exchanges_lookup.csv` (60 exchanges).
3. **US tickers** have no suffix, so they are mapped through SEC's
   `company_tickers_exchange.json` (Nasdaq / NYSE / Cboe / OTC).
4. **ADRs**: a foreign company whose only ticker is a US listing (Toyota `TM`, TSMC `TSM`,
   HSBC `HSBC`, Shell `SHEL`) is attributed to its **home exchange**, not the US one.
   Otherwise Tokyo and London would lose their biggest names to New York.

## Files

| Path | What it is |
|---|---|
| `data/exchanges.csv` | 60 exchanges: companies, total market cap, top-10 market cap, largest company |
| `data/exchange_top_companies.csv` | **top 10 companies per exchange** with ticker, market cap, revenue |
| `data/exchange_companies.csv` | every assigned company (9,780) with its exchange |
| `data/exchanges_lookup.csv` | suffix → exchange / country / city reference |
| `charts/sm01_exchanges_market_cap.png` | the 20 largest exchanges by market value |

## The big ones

| Exchange | Country | Companies | Market value | Largest company |
|---|---|---|---|---|
| Nasdaq | US | 1,618 | $46.1T | NVIDIA |
| New York Stock Exchange | US | 1,467 | $34.2T | Berkshire Hathaway |
| Tokyo Stock Exchange | Japan | 903 | $7.8T | Mitsubishi UFJ |
| Shanghai Stock Exchange | China | 161 | $5.4T | China Construction Bank |
| London Stock Exchange | UK | 464 | $4.6T | HSBC |
| Toronto Stock Exchange | Canada | 394 | $4.2T | Royal Bank of Canada |
| Taiwan Stock Exchange | Taiwan | 95 | $4.1T | TSMC |
| Hong Kong Stock Exchange | Hong Kong | 306 | $4.0T | ICBC |
| National Stock Exchange of India | India | 564 | $3.8T | Reliance Industries |
| Korea Exchange (KOSPI) | South Korea | 159 | $3.3T | Samsung |

## Caveats — read before quoting

1. **This is the top ~10,000 listed companies, not every listing.** Small exchanges are
   thin: Budapest 2 companies, Prague 4, Bombay 5 (CMC uses NSE tickers for India, so
   BSE barely appears), Buenos Aires 3. Empty-looking exchanges mean *coverage*, not
   absence of a market.
2. **Market values are an October 2026 snapshot** from companiesmarketcap, not audited.
3. **ADR attribution is a judgement call.** Toyota on Tokyo and TSMC on Taiwan is what a
   reader expects; but the same rule also moves Arm, Linde, Spotify and Ferrari to their
   home exchanges even though their primary listing is in New York. The `ticker` column
   shows which is which.
4. **Totals are not world market cap.** The 9,780 companies here sum to ~$148T, which
   includes some double counting across listings and excludes the ~40,000 smaller
   listings. Never present it as "the world's stock market value".
5. **Revenue is only present where the listed-universe pass found it** (see
   `listed_universe/README.md`).

## Rebuild

```powershell
$py = "C:\Users\abhijit\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
& $py stock_market/scripts/build_exchanges.py
& $py stock_market/scripts/make_chart.py
```

## History: how each country's market grew (added Oct 2026)

`scripts/fetch_history.py` downloads, and `site/build/market_history.py` turns into the
"How each country's stock market has performed" section of `site/markets.html`:

| File | What it is |
|---|---|
| `data/index_monthly.csv` | Month-end close of 27 main indexes (Yahoo Finance), from 1985–2012 depending on the index |
| `data/fx_monthly.csv` | Local currency per US$, monthly average (FRED; Yahoo for IDR, ARS, ILS, TRY; pre-1999 euro from legacy currencies at the fixed rates) |
| `data/wb_market_history.csv` | World Bank market cap (US$, % of GDP) and listed companies, every country, 1975–2025 |

Checks done: 12 index closes for Dec 2024 match the official closes exactly (an earlier
time-zone bug had shifted Asian/European months by one; fixed). October 2026 falls in KOSPI
and Jakarta were checked against news reports. World Bank reporting errors are removed: a
fixed list (India 2018 and 2025 NSE+BSE double count, Iran, etc.) plus an automatic rule for
1–2 year blips more than 3x off both neighbours. Every removed point is listed on the page.

Not covered by index history: Saudi Arabia, Thailand, Philippines, Vietnam, Russia (no free
monthly data). Indexes are price-only (no dividends).

```
python stock_market/scripts/fetch_history.py
python site/build/market_history.py
```
