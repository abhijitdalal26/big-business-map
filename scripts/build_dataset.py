"""Build a clean dataset from the Forbes Global 2000 API JSON.

Usage: python scripts/build_dataset.py [year] [rawdir]   (default 2026, data/raw_2026)

Input : <rawdir>/global2000_<year>_api.json
Output: data/global2000_<year>.csv          (one row per company, current-year metrics)
        data/global2000_<year>_history.csv  (long format, 10-year metric history)
        output/summary.txt                (headline aggregates)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import numpy as np

YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
RAW = Path(sys.argv[2] if len(sys.argv) > 2 else f"data/raw_{YEAR}") / f"global2000_{YEAR}_api.json"
OUT_DIR = Path("data")
OUT_DIR.mkdir(parents=True, exist_ok=True)

REGION = {
    # North America
    "United States": "North America",
    "Canada": "North America",
    "Bermuda": "North America",
    "Cayman Islands": "North America",
    # Latin America
    "Mexico": "Latin America",
    "Brazil": "Latin America",
    "Chile": "Latin America",
    "Colombia": "Latin America",
    "Peru": "Latin America",
    "Argentina": "Latin America",
    "Panama": "Latin America",
    "Uruguay": "Latin America",
    # Europe
    "United Kingdom": "Europe",
    "Germany": "Europe",
    "France": "Europe",
    "Switzerland": "Europe",
    "Netherlands": "Europe",
    "Spain": "Europe",
    "Italy": "Europe",
    "Sweden": "Europe",
    "Denmark": "Europe",
    "Norway": "Europe",
    "Finland": "Europe",
    "Belgium": "Europe",
    "Austria": "Europe",
    "Ireland": "Europe",
    "Luxembourg": "Europe",
    "Poland": "Europe",
    "Portugal": "Europe",
    "Greece": "Europe",
    "Czech Republic": "Europe",
    "Hungary": "Europe",
    "Romania": "Europe",
    "Slovenia": "Europe",
    "Cyprus": "Europe",
    "Turkey": "Europe",
    # Middle East & Central Asia
    "Saudi Arabia": "Middle East & Central Asia",
    "United Arab Emirates": "Middle East & Central Asia",
    "Israel": "Middle East & Central Asia",
    "Qatar": "Middle East & Central Asia",
    "Kuwait": "Middle East & Central Asia",
    "Bahrain": "Middle East & Central Asia",
    "Oman": "Middle East & Central Asia",
    "Jordan": "Middle East & Central Asia",
    "Lebanon": "Middle East & Central Asia",
    "Kazakhstan": "Middle East & Central Asia",
    "Pakistan": "Middle East & Central Asia",
    # Africa
    "South Africa": "Africa",
    "Egypt": "Africa",
    "Morocco": "Africa",
    "Nigeria": "Africa",
    # Asia-Pacific
    "China": "Asia-Pacific",
    "Japan": "Asia-Pacific",
    "India": "Asia-Pacific",
    "South Korea": "Asia-Pacific",
    "Taiwan": "Asia-Pacific",
    "Hong Kong": "Asia-Pacific",
    "Singapore": "Asia-Pacific",
    "Australia": "Asia-Pacific",
    "Indonesia": "Asia-Pacific",
    "Malaysia": "Asia-Pacific",
    "Thailand": "Asia-Pacific",
    "Philippines": "Asia-Pacific",
    "Vietnam": "Asia-Pacific",
}

HISTORY = {
    "revenueList": "revenue",
    "profitList": "profits",
    "assetsList": "assets",
    "employeesList": "employees",
}


def main() -> None:
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    rows = raw["organizationList"]["organizationsLists"]
    print(f"records: {len(rows)}")

    records, history = [], []
    for r in rows:
        rec = {
            "rank": r.get("rank"),
            "company": r.get("organizationName") or r.get("name"),
            "uri": r.get("uri"),
            "country": r.get("country"),
            "region": REGION.get(r.get("country"), "Other"),
            "industry": r.get("industry"),
            "city": r.get("city"),
            "state": r.get("state"),
            "ceo": r.get("ceoName"),
            "ceo_title": r.get("ceoTitle"),
            "year_founded": r.get("yearFounded"),
            "website": r.get("webSite"),
            "image": r.get("image") if r.get("imageExists") else None,
            # Forbes reports financials in USD millions
            "revenue_musd": r.get("revenue"),
            "profits_musd": r.get("profits"),
            "assets_musd": r.get("assets"),
            "market_value_musd": r.get("marketValue"),
            "employees": r.get("employees"),
            "revenue_rank": r.get("revenueRank"),
            "profits_rank": r.get("profitsRank"),
            "assets_rank": r.get("assetsRank"),
            "market_value_rank": r.get("marketValueRank"),
            "description": (r.get("description") or "").strip(),
        }
        records.append(rec)

        for field, metric in HISTORY.items():
            series = r.get(field) or []
            for i, val in enumerate(series):
                if val is None:
                    continue
                history.append(
                    {
                        "company": rec["company"],
                        "country": rec["country"],
                        "industry": rec["industry"],
                        "metric": metric,
                        "years_ago": i,
                        "approx_year": YEAR - 1 - i,
                        "value": float(val),
                        "unit": "employees" if metric == "employees" else "USD millions",
                    }
                )

    df = pd.DataFrame(records)

    # Derived ratios (guard against zero / null denominators)
    rev = df["revenue_musd"].astype(float).replace(0, np.nan)
    assets = df["assets_musd"].astype(float).replace(0, np.nan)
    emp = df["employees"].astype(float).replace(0, np.nan)
    df["profit_margin_pct"] = (df["profits_musd"] / rev * 100).round(2)
    df["roa_pct"] = (df["profits_musd"] / assets * 100).round(2)
    df["asset_turnover"] = (rev / assets).round(3)
    df["revenue_per_employee_usd"] = (rev * 1e6 / emp).round(0)
    df["profit_per_employee_usd"] = (df["profits_musd"] * 1e6 / emp).round(0)
    df["market_value_to_revenue"] = (df["market_value_musd"] / rev).round(2)

    df = df.sort_values("rank").reset_index(drop=True)

    csv_path = OUT_DIR / f"global2000_{YEAR}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"wrote {csv_path}  shape={df.shape}")

    hist = pd.DataFrame(history)
    hist_path = OUT_DIR / f"global2000_{YEAR}_history.csv"
    hist.to_csv(hist_path, index=False, encoding="utf-8-sig")
    print(f"wrote {hist_path}  shape={hist.shape}")

    # ---- summary ----
    lines = []
    total_rev = df["revenue_musd"].sum()
    lines.append(f"Companies: {len(df)}")
    lines.append(f"Total revenue: ${total_rev/1e6:,.2f} trillion")
    lines.append(f"Total profits: ${df['profits_musd'].sum()/1e6:,.2f} trillion")
    lines.append(f"Total assets:  ${df['assets_musd'].sum()/1e6:,.2f} trillion")
    lines.append(f"Total market value: ${df['market_value_musd'].sum()/1e6:,.2f} trillion")
    lines.append(f"Total employees: {df['employees'].sum():,.0f}")
    lines.append("")
    lines.append("Top 10 countries by company count:")
    lines.append(df["country"].value_counts().head(10).to_string())
    lines.append("")
    lines.append("Top 15 industries by company count:")
    lines.append(df["industry"].value_counts().head(15).to_string())
    lines.append("")
    lines.append("Companies per region:")
    lines.append(df["region"].value_counts().to_string())
    lines.append("")
    lines.append("Top 10 by revenue ($M):")
    top = df.nlargest(10, "revenue_musd")[["rank", "company", "country", "revenue_musd"]]
    lines.append(top.to_string(index=False))
    lines.append("")
    lines.append("Top 10 by market value ($M):")
    top = df.nlargest(10, "market_value_musd")[["rank", "company", "country", "market_value_musd"]]
    lines.append(top.to_string(index=False))

    out = Path("output")
    out.mkdir(exist_ok=True)
    (out / ("summary.txt" if YEAR == 2025 else f"summary_{YEAR}.txt")).write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
