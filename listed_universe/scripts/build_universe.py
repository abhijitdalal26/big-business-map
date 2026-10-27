"""Merge the SEC (authoritative) and companiesmarketcap (estimate) universes.

Rule: when both sources describe the same company, keep the SEC revenue and mark
the row `authoritative`; CMC revenue is only used where SEC has nothing, and is
marked `estimate`. Nothing is averaged, ever.

Output: listed_universe/data/listed_universe.csv
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

OUT = Path(__file__).resolve().parents[1] / "data"

SUFFIXES = {
    "inc", "corp", "corporation", "co", "company", "ltd", "limited", "plc",
    "ag", "sa", "nv", "se", "spa", "group", "holding", "holdings", "the",
    "class", "a", "b", "ordinary", "shares", "adr",
}


def norm(name: str) -> str:
    s = str(name).lower().replace("&", " and ")
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return " ".join(t for t in s.split() if t and t not in SUFFIXES)


COUNTRY_FIX = {
    "USA": "United States", "UK": "United Kingdom", "S. Arabia": "Saudi Arabia",
    "S. Korea": "South Korea", "UAE": "United Arab Emirates", "Russia": "Russia",
    "Vietnam": "Vietnam", "Czech Republic": "Czech Republic",
}


def main() -> None:
    sec = pd.read_csv(OUT / "sec_us_revenue.csv")
    cmc = pd.read_csv(OUT / "cmc_list.csv")
    cmc["country"] = cmc["country"].replace(COUNTRY_FIX)
    rev_path = OUT / "cmc_revenue.csv"

    cmc_rev = (pd.read_csv(rev_path)[["slug", "revenue_usd", "revenue_period"]]
               if rev_path.exists() else
               pd.DataFrame(columns=["slug", "revenue_usd", "revenue_period"]))
    cmc = cmc.merge(cmc_rev, on="slug", how="left")

    sec["key"] = sec["entity_name"].map(norm)
    cmc["key"] = cmc["name"].map(norm)

    # match SEC filers to CMC rows: ticker first (unambiguous), then exact name
    cik_map = pd.read_csv(OUT / "sec_cik_ticker.csv")
    cik_to_ticker = dict(zip(cik_map["cik"], cik_map["ticker"]))
    cmc_ticker: dict[str, int] = {}
    for i, t in enumerate(cmc["ticker"].fillna("")):
        if t:
            cmc_ticker.setdefault(t.upper(), i)

    match_idx: dict[int, int] = {}
    for i, r in sec.iterrows():
        t = cik_to_ticker.get(r["cik"])
        if t and t in cmc_ticker:
            match_idx[i] = cmc_ticker[t]

    name_idx = {k: i for i, k in enumerate(cmc["key"].fillna("")) if k}
    for i, k in enumerate(sec["key"].fillna("")):
        if i in match_idx or not k:
            continue
        if k in name_idx:
            match_idx[i] = name_idx[k]

    sec_matched = set(match_idx.values())

    rows = []
    for i, r in sec.iterrows():
        j = match_idx.get(i)
        rows.append({
            "company": r["entity_name"],
            "ticker_or_slug": cmc.at[j, "slug"] if j is not None else None,
            "country": cmc.at[j, "country"] if j is not None else "United States",
            "market_cap_usd": cmc.at[j, "market_cap_usd"] if j is not None else None,
            "revenue_usd": r["revenue_usd"],
            "revenue_year": r["period"],
            "revenue_source": "SEC XBRL (audited)",
            "confidence": "authoritative",
            "cik": r["cik"],
        })

    for j, r in cmc.iterrows():
        if j in sec_matched:
            continue
        rows.append({
            "company": r["name"],
            "ticker_or_slug": r["slug"],
            "country": r["country"],
            "market_cap_usd": r["market_cap_usd"],
            "revenue_usd": r["revenue_usd"] if pd.notna(r.get("revenue_usd")) else None,
            "revenue_year": r.get("revenue_period"),
            "revenue_source": "companiesmarketcap (estimate)" if pd.notna(r.get("revenue_usd")) else None,
            "confidence": "estimate" if pd.notna(r.get("revenue_usd")) else "market-cap only",
            "cik": None,
        })

    df = pd.DataFrame(rows)

    # sanity: revenue that dwarfs market cap by >50x, or above $2T, is a known
    # companiesmarketcap data error (e.g. Severstal is listed at $874B).
    bad = (df["revenue_usd"].notna()) & (
        (df["revenue_usd"] > 2e12) |
        ((df["market_cap_usd"].notna()) & (df["revenue_usd"] > 50 * df["market_cap_usd"]))
    )
    df.loc[bad, "revenue_usd"] = None
    df.loc[bad, "revenue_source"] = "rejected: implausible value"
    df.loc[bad, "confidence"] = "market-cap only"

    df = df.sort_values("revenue_usd", ascending=False, na_position="last")
    df.to_csv(OUT / "listed_universe.csv", index=False, encoding="utf-8-sig")

    print(f"wrote {OUT / 'listed_universe.csv'} rows={len(df)}")
    print(df["confidence"].value_counts().to_string())
    print(f"matched SEC<->CMC: {len(sec_matched):,} of {len(sec):,} SEC filers")
    with_rev = df[df["revenue_usd"].notna()]
    print(f"rows with revenue: {len(with_rev):,}")
    print(f"revenue > $1B: {(with_rev['revenue_usd'] > 1e9).sum():,}")
    print(f"revenue > $10B: {(with_rev['revenue_usd'] > 1e10).sum():,}")


if __name__ == "__main__":
    main()
