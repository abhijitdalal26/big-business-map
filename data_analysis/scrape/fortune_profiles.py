"""Mine the saved Fortune company pages for fields the CSV does not carry.

``data/fortune_g500_2025.csv`` was built by scraping the ranking table. It
has revenue, profit, market value and headcount -- but no industry, no
country and no "as of" date. Every company profile page saved under
``data/raw/fortune/`` embeds a ``__NEXT_DATA__`` JSON blob that contains all
of that, so we re-read the local copies (no further network traffic) and
recover the missing fields.

The recovered file also carries a *fresher market-value date* than Forbes
uses, which matters: Forbes' market values are a May 2025 snapshot while
Fortune's pages were re-rendered in September 2026. The two must never be
plotted as if they were the same vintage.

Output: ``output/raw/fortune_profiles.csv``
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from config import ROOT

FORTUNE_DIR = ROOT / "data" / "raw" / "fortune"
NEXT_DATA = re.compile(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)

WANTED = {
    "Revenues ($M)": "revenues_musd",
    "Profits ($M)": "profits_musd",
    "Market value ($M)": "market_value_musd",
    "Number of employees": "employees",
    "Industry": "industry",
    "Company type": "company_type_page",
    "Country/Territory": "country",
    "Headquarters": "headquarters_page",
    "CEO": "ceo_page",
    "Ticker": "ticker_page",
    "Website": "website",
}


def to_number(v):
    if v is None:
        return None
    s = str(v).replace(",", "").replace("$", "").strip()
    if not s or s.lower() in {"n/a", "none", "-"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_file(path: Path) -> dict | None:
    try:
        html = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    m = NEXT_DATA.search(html)
    if not m:
        return None
    try:
        blob = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None
    info = blob.get("props", {}).get("pageProps", {}).get("company", {})
    info = info.get("companyInfo") or {}
    if not info:
        return None

    rec: dict = {"slug": path.stem}
    for src, dst in WANTED.items():
        val = info.get(src)
        if dst.endswith("_musd") or dst == "employees":
            rec[dst] = to_number(val)
        else:
            rec[dst] = val if val is not None else ""
    rec["fortune_updated"] = info.get("Updated", "") or ""
    rec["market_value_asof"] = ""
    foot = info.get("Footnote", "") or ""
    m2 = re.search(r"Market Value as of ([A-Za-z]+\.? \d{1,2}, \d{4})", foot)
    if m2:
        rec["market_value_asof"] = m2.group(1)
    return rec


def main() -> pd.DataFrame:
    files = sorted(FORTUNE_DIR.glob("*.html"))
    print(f"scanning {len(files)} saved Fortune pages ...")
    rows = []
    for i, f in enumerate(files, 1):
        r = parse_file(f)
        if r:
            rows.append(r)
        if i % 100 == 0:
            print(f"  {i}/{len(files)}")

    df = pd.DataFrame(rows)
    if len(df):
        df = df.drop_duplicates(subset=["slug"])
        df = df.sort_values("slug")
    out = Path(__file__).resolve().parent.parent / "output" / "raw"
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "fortune_profiles.csv", index=False, encoding="utf-8")

    if len(df):
        print(f"\nparsed {len(df)}/{len(files)} pages")
        print("  with employees :", int(df["employees"].notna().sum()))
        print("  with industry  :", int((df["industry"].astype(str).str.len() > 0).sum()))
        print("  with country   :", int((df["country"].astype(str).str.len() > 0).sum()))
        print("  market value asof examples:",
              df["market_value_asof"].dropna().unique()[:3].tolist())
    print(f"written -> {out / 'fortune_profiles.csv'}")
    return df


if __name__ == "__main__":
    main()
