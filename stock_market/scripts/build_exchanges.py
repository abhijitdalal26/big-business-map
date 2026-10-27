"""Stock-exchange view: top companies per exchange, worldwide.

Two classification routes:
  - non-US tickers carry a suffix (.NS, .T, .L, .PA ...) -> exchange registry below
  - US tickers are mapped through SEC's company_tickers_exchange.json (NYSE / Nasdaq / OTC)

Outputs:
  stock_market/data/exchanges.csv              one row per exchange with totals
  stock_market/data/exchange_top_companies.csv top 10 per exchange
  stock_market/data/exchanges_lookup.csv       suffix -> exchange reference table
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
SRC = BASE.parent / "listed_universe" / "data"

# ticker suffix -> (exchange, country, city)
SUFFIX_MAP: dict[str, tuple[str, str, str]] = {
    "T": ("Tokyo Stock Exchange", "Japan", "Tokyo"),
    "NS": ("National Stock Exchange of India", "India", "Mumbai"),
    "BO": ("Bombay Stock Exchange", "India", "Mumbai"),
    "L": ("London Stock Exchange", "United Kingdom", "London"),
    "AX": ("Australian Securities Exchange", "Australia", "Sydney"),
    "PA": ("Euronext Paris", "France", "Paris"),
    "TO": ("Toronto Stock Exchange", "Canada", "Toronto"),
    "V": ("TSX Venture Exchange", "Canada", "Calgary"),
    "SR": ("Saudi Exchange (Tadawul)", "Saudi Arabia", "Riyadh"),
    "HK": ("Hong Kong Stock Exchange", "Hong Kong", "Hong Kong"),
    "ST": ("Nasdaq Stockholm", "Sweden", "Stockholm"),
    "DE": ("Xetra (Frankfurt)", "Germany", "Frankfurt"),
    "F": ("Frankfurt Stock Exchange", "Germany", "Frankfurt"),
    "SW": ("SIX Swiss Exchange", "Switzerland", "Zurich"),
    "SS": ("Shanghai Stock Exchange", "China", "Shanghai"),
    "SZ": ("Shenzhen Stock Exchange", "China", "Shenzhen"),
    "KS": ("Korea Exchange (KOSPI)", "South Korea", "Seoul"),
    "KQ": ("KOSDAQ", "South Korea", "Seoul"),
    "MI": ("Borsa Italiana", "Italy", "Milan"),
    "MC": ("Bolsa de Madrid", "Spain", "Madrid"),
    "AS": ("Euronext Amsterdam", "Netherlands", "Amsterdam"),
    "BR": ("Euronext Brussels", "Belgium", "Brussels"),
    "LS": ("Euronext Lisbon", "Portugal", "Lisbon"),
    "OL": ("Oslo Børs", "Norway", "Oslo"),
    "HE": ("Nasdaq Helsinki", "Finland", "Helsinki"),
    "CO": ("Nasdaq Copenhagen", "Denmark", "Copenhagen"),
    "VI": ("Vienna Stock Exchange", "Austria", "Vienna"),
    "IR": ("Euronext Dublin", "Ireland", "Dublin"),
    "WA": ("Warsaw Stock Exchange", "Poland", "Warsaw"),
    "PR": ("Prague Stock Exchange", "Czech Republic", "Prague"),
    "BD": ("Budapest Stock Exchange", "Hungary", "Budapest"),
    "IS": ("Borsa Istanbul", "Turkey", "Istanbul"),
    "TA": ("Tel Aviv Stock Exchange", "Israel", "Tel Aviv"),
    "JK": ("Indonesia Stock Exchange", "Indonesia", "Jakarta"),
    "KL": ("Bursa Malaysia", "Malaysia", "Kuala Lumpur"),
    "BK": ("Stock Exchange of Thailand", "Thailand", "Bangkok"),
    "QA": ("Qatar Stock Exchange", "Qatar", "Doha"),
    "KW": ("Boursa Kuwait", "Kuwait", "Kuwait City"),
    "OM": ("Muscat Stock Exchange", "Oman", "Muscat"),
    "BH": ("Bahrain Bourse", "Bahrain", "Manama"),
    "AE": ("Abu Dhabi Securities Exchange", "United Arab Emirates", "Abu Dhabi"),
    "DFM": ("Dubai Financial Market", "United Arab Emirates", "Dubai"),
    "MX": ("Mexican Stock Exchange (BMV)", "Mexico", "Mexico City"),
    "SA": ("B3 (Brasil Bolsa Balcão)", "Brazil", "São Paulo"),
    "CL": ("Colombia Stock Exchange", "Colombia", "Bogotá"),
    "BA": ("Buenos Aires Stock Exchange", "Argentina", "Buenos Aires"),
    "SN": ("Santiago Stock Exchange", "Chile", "Santiago"),
    "JO": ("Johannesburg Stock Exchange", "South Africa", "Johannesburg"),
    "EGX": ("Egyptian Exchange", "Egypt", "Cairo"),
    "NZ": ("New Zealand Exchange", "New Zealand", "Wellington"),
    "SG": ("Singapore Exchange", "Singapore", "Singapore"),
    "TW": ("Taiwan Stock Exchange", "Taiwan", "Taipei"),
    "TWO": ("Taipei Exchange", "Taiwan", "Taipei"),
    "ME": ("Moscow Exchange", "Russia", "Moscow"),
    "ATH": ("Athens Stock Exchange", "Greece", "Athens"),
    "LU": ("Luxembourg Stock Exchange", "Luxembourg", "Luxembourg"),
    "ZAG": ("Zagreb Stock Exchange", "Croatia", "Zagreb"),
    "VN": ("Hanoi Stock Exchange", "Vietnam", "Hanoi"),
    "HM": ("Ho Chi Minh Stock Exchange", "Vietnam", "Ho Chi Minh City"),
}


COUNTRY_TO_EXCHANGE = {
    "Japan": "Tokyo Stock Exchange", "UK": "London Stock Exchange",
    "United Kingdom": "London Stock Exchange", "Taiwan": "Taiwan Stock Exchange",
    "China": "Hong Kong Stock Exchange", "Hong Kong": "Hong Kong Stock Exchange",
    "France": "Euronext Paris", "Germany": "Xetra (Frankfurt)",
    "Switzerland": "SIX Swiss Exchange", "Netherlands": "Euronext Amsterdam",
    "Spain": "Bolsa de Madrid", "Italy": "Borsa Italiana",
    "Sweden": "Nasdaq Stockholm", "Denmark": "Nasdaq Copenhagen",
    "Norway": "Oslo Børs", "Finland": "Nasdaq Helsinki",
    "Belgium": "Euronext Brussels", "Portugal": "Euronext Lisbon",
    "Ireland": "Euronext Dublin", "Canada": "Toronto Stock Exchange",
    "Australia": "Australian Securities Exchange",
    "India": "National Stock Exchange of India",
    "S. Korea": "Korea Exchange (KOSPI)", "South Korea": "Korea Exchange (KOSPI)",
    "Brazil": "B3 (Brasil Bolsa Balcão)", "Mexico": "Mexican Stock Exchange (BMV)",
    "S. Arabia": "Saudi Exchange (Tadawul)", "Saudi Arabia": "Saudi Exchange (Tadawul)",
    "UAE": "Abu Dhabi Securities Exchange", "Israel": "Tel Aviv Stock Exchange",
    "Singapore": "Singapore Exchange", "South Africa": "Johannesburg Stock Exchange",
    "Russia": "Moscow Exchange", "Turkey": "Borsa Istanbul",
    "Indonesia": "Indonesia Stock Exchange", "Thailand": "Stock Exchange of Thailand",
    "Malaysia": "Bursa Malaysia", "Poland": "Warsaw Stock Exchange",
    "Greece": "Athens Stock Exchange", "Austria": "Vienna Stock Exchange",
    "Luxembourg": "Luxembourg Stock Exchange", "Philippines": "Philippine Stock Exchange",
    "Vietnam": "Ho Chi Minh Stock Exchange",
}


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    lst = pd.read_csv(SRC / "cmc_list.csv")
    rev = pd.read_csv(SRC / "cmc_revenue.csv")[["slug", "revenue_usd"]]
    df = lst.merge(rev, on="slug", how="left")

    # SEC mapping for US tickers
    cache = DATA / "sec_tickers_exchange.csv"
    if not cache.exists():
        r = requests.get("https://www.sec.gov/files/company_tickers_exchange.json",
                         headers={"User-Agent": "earth-atlas-research admin@example.com"},
                         timeout=60)
        j = r.json()
        pd.DataFrame(j["data"], columns=j["fields"]).to_csv(
            cache, index=False, encoding="utf-8-sig")
    sec = pd.read_csv(cache)
    ticker_to_ex = {str(t).upper(): e for t, e in zip(sec["ticker"], sec["exchange"])}
    ex_name = {"Nasdaq": "Nasdaq", "NYSE": "New York Stock Exchange",
               "Cboe": "Cboe (US)", "OTC": "OTC Markets (US)"}

    rows = []
    for r in df.itertuples():
        t = str(r.ticker) if pd.notna(r.ticker) else ""
        ex = country = city = None
        if "." in t:
            suffix = t.rsplit(".", 1)[1].upper()
            if suffix in SUFFIX_MAP:
                ex, country, city = SUFFIX_MAP[suffix]
        if ex is None and t:
            sec_ex = ticker_to_ex.get(t.upper())
            if sec_ex:
                if str(r.country) not in {"USA", "United States"} and str(r.country) in COUNTRY_TO_EXCHANGE:
                    # US-listed ADR of a foreign company: attribute to home exchange
                    ex = COUNTRY_TO_EXCHANGE[str(r.country)]
                else:
                    ex = ex_name.get(sec_ex, f"{sec_ex} (US)")
                    country, city = "United States", "New York"
        if ex is None:
            continue
        meta = {v[0]: (v[1], v[2]) for v in SUFFIX_MAP.values()}.get(ex)
        if meta:
            country, city = meta
        if ex == "Nasdaq" or ex == "New York Stock Exchange":
            country, city = "United States", "New York"
        rows.append({"exchange": ex, "exchange_country": country, "city": city,
                     "company": r.name, "ticker": t,
                     "market_cap_usd": r.market_cap_usd, "revenue_usd": r.revenue_usd})

    ex_df = pd.DataFrame(rows)
    ex_df = ex_df.sort_values(["exchange", "market_cap_usd"], ascending=[True, False])
    ex_df["rank_in_exchange"] = ex_df.groupby("exchange").cumcount() + 1

    ex_df.to_csv(DATA / "exchange_companies.csv", index=False, encoding="utf-8-sig")
    top = ex_df[ex_df["rank_in_exchange"] <= 10]
    top.to_csv(DATA / "exchange_top_companies.csv", index=False, encoding="utf-8-sig")

    tot = ex_df.groupby(["exchange", "exchange_country", "city"], as_index=False).agg(
        companies=("company", "count"),
        total_market_cap_usd=("market_cap_usd", "sum"),
        top10_market_cap_usd=("market_cap_usd", lambda s: s.nlargest(10).sum()))
    best = ex_df.loc[ex_df.groupby("exchange")["market_cap_usd"].idxmax(),
                     ["exchange", "company", "market_cap_usd"]]
    best = best.rename(columns={"company": "top_company", "market_cap_usd": "top_company_mcap"})
    summary = tot.merge(best, on="exchange", how="left")
    summary = summary.sort_values("total_market_cap_usd", ascending=False)
    summary.to_csv(DATA / "exchanges.csv", index=False, encoding="utf-8-sig")

    lookup = pd.DataFrame(
        [{"suffix": k, "exchange": v[0], "country": v[1], "city": v[2]}
         for k, v in SUFFIX_MAP.items()])
    lookup.to_csv(DATA / "exchanges_lookup.csv", index=False, encoding="utf-8-sig")

    print(f"exchanges identified: {summary.exchange.nunique()}")
    print(f"companies assigned: {len(ex_df):,} of {len(df):,}")
    print(summary.head(20)[["exchange", "exchange_country", "companies",
                            "total_market_cap_usd"]].to_string(index=False))


if __name__ == "__main__":
    main()
