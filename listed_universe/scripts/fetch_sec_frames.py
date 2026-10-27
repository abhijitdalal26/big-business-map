"""US-listed companies with revenue, from SEC XBRL frames (authoritative).

The frames API returns every filer that reported a given us-gaap concept for a
calendar period, which is far cheaper than downloading per-company fact files.

Output: listed_universe/data/sec_us_revenue.csv
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

BASE = "https://data.sec.gov/api/xbrl/frames/us-gaap"
HEADERS = {"User-Agent": "earth-atlas-research admin@example.com"}
OUT = Path(__file__).resolve().parents[1] / "data"

# Revenue concepts, in preference order (first match per CIK wins).
TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "SalesRevenueNet",
    "SalesRevenueGoodsNet",
    "RevenuesNetOfInterestExpense",          # banks
    "InterestAndDividendIncomeOperating",     # banks
]

PERIODS = ["CY2025", "CY2024"]


def get_frames(tag: str, period: str):
    url = f"{BASE}/{tag}/USD/{period}.json"
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except Exception as exc:  # noqa: BLE001
            print(f"    retry {tag}/{period}: {exc}")
            time.sleep(1.5 * (attempt + 1))
    return None


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows: dict[int, dict] = {}

    for period in PERIODS:
        for tag in TAGS:
            data = get_frames(tag, period)
            if not data:
                continue
            n_new = 0
            for rec in data.get("data", []):
                cik = rec.get("cik")
                val = rec.get("val")
                if cik is None or val is None:
                    continue
                if cik in rows:            # already have a preferred tag
                    continue
                rows[cik] = {
                    "cik": cik,
                    "entity_name": rec.get("entityName"),
                    "revenue_usd": float(val),
                    "period": period,
                    "tag": tag,
                    "filed": rec.get("filed"),
                }
                n_new += 1
            print(f"  {period} {tag}: +{n_new} (total {len(rows)})")
            time.sleep(0.15)

    df = pd.DataFrame(rows.values()).sort_values("revenue_usd", ascending=False)
    df.to_csv(OUT / "sec_us_revenue.csv", index=False, encoding="utf-8-sig")
    print(f"\nwrote {OUT / 'sec_us_revenue.csv'} rows={len(df)}")
    print(f"companies with revenue > $1B: {(df.revenue_usd > 1e9).sum():,}")
    print(df.head(10)[["entity_name", "revenue_usd", "period", "tag"]].to_string(index=False))


if __name__ == "__main__":
    main()
