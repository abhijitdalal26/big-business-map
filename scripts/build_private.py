"""Forbes' America's Largest Private Companies -> data/private_us_<year>.csv

Usage: python scripts/build_private.py [year] [rawdir]   (default 2026, data/raw_2026)

The only free, curated list of large private companies. 200 rows, US-only, with
revenue and headcount but no profit or assets (private firms don't file them).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
RAW = Path(sys.argv[2] if len(sys.argv) > 2 else f"data/raw_{YEAR}") / f"largest_private_{YEAR}_api.json"
OUT = f"data/private_us_{YEAR}.csv"


def main() -> None:
    data = json.loads(RAW.read_text(encoding="utf-8"))
    rows = data["organizationList"]["organizationsLists"]
    print(f"records: {len(rows)}")

    out = []
    for r in rows:
        out.append({
            "rank": r.get("rank"),
            "company": r.get("organizationName"),
            "uri": r.get("uri"),
            "country": r.get("country"),
            "industry": (r.get("industry") or "").strip() or None,
            "city": r.get("city"),
            "state": r.get("state"),
            "ceo": r.get("ceoName"),
            "year_founded": r.get("yearFounded"),
            "website": r.get("webSite"),
            "revenue_musd": r.get("revenue"),
            "revenue_change_pct": r.get("revenueChange"),
            "employees": r.get("employees"),
            "description": (r.get("description") or "").strip() or None,
        })

    df = pd.DataFrame(out).sort_values("rank").reset_index(drop=True)
    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"wrote {OUT} rows={len(df)}")
    print(f"total revenue: ${df['revenue_musd'].sum()/1e6:,.2f}T")
    print(f"total employees: {df['employees'].sum():,.0f}")
    print(df.head(10)[["rank", "company", "industry", "revenue_musd", "employees"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()
