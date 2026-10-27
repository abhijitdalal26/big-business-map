"""Global startup / unicorn dataset.

Sources:
  - CB Insights Unicorn Board (public page, 1,447 companies)  -> valuation, country,
    city, industry, investors, date joined
  - Forbes Cloud 100 + Next Billion-Dollar Startups (already collected)

Outputs:
  startups/data/unicorns_cbinsights.csv
  startups/data/startups_global.csv     (merged, deduped)
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import requests
from lxml import html

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
DATA.mkdir(parents=True, exist_ok=True)

URL = "https://www.cbinsights.com/research-unicorn-companies"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"}


def norm(name: str) -> str:
    s = str(name).lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\b(inc|corp|corporation|co|ltd|limited|plc|technologies|technology|labs|"
               r"group|holdings|holding|the)\b", " ", s)
    return " ".join(s.split())


def fetch_unicorns() -> pd.DataFrame:
    resp = requests.get(URL, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    doc = html.fromstring(resp.content)
    rows = []
    for tr in doc.xpath("//tr"):
        tds = tr.xpath("./td")
        if len(tds) != 7:
            continue
        vals = [" ".join(td.text_content().split()) for td in tds]
        company, val, joined, country, city, industry, investors = vals
        m = re.search(r"[\d,]+(?:\.\d+)?", val)
        rows.append({
            "company": company,
            "valuation_busd": float(m.group(0).replace(",", "")) if m else None,
            "date_joined": joined,
            "country": country,
            "city": city,
            "industry": industry,
            "investors": investors,
        })
    return pd.DataFrame(rows)


def main() -> None:
    cb = fetch_unicorns()
    cb = cb.sort_values("valuation_busd", ascending=False)
    cb = cb.drop_duplicates("company", keep="first").reset_index(drop=True)

    KNOWN = {"Enterprise Tech", "Financial Services", "Industrials", "Consumer & Retail",
             "Healthcare & Life Sciences", "Media & Entertainment", "Insurance",
             "Industrial", "Health", "Energy", "Real Estate"}
    fix = {"Industrial": "Industrials", "Health": "Healthcare & Life Sciences"}
    cb["industry"] = cb["industry"].where(cb["industry"].isin(KNOWN))
    cb["industry"] = cb["industry"].replace(fix)
    cb.insert(0, "rank", cb.index + 1)
    cb.to_csv(DATA / "unicorns_cbinsights.csv", index=False, encoding="utf-8-sig")
    print(f"CB Insights: {len(cb)} unicorns, total ${cb.valuation_busd.sum():,.0f}B")

    forbes_path = BASE.parent / "data" / "startups_2025.csv"
    frames = []
    if forbes_path.exists():
        fs = pd.read_csv(forbes_path)
        fs["key"] = fs["company"].map(norm)
        frames.append(fs[["key", "company", "list", "country", "industry",
                          "valuation_musd", "funding_musd", "employees"]])

    cb["key"] = cb["company"].map(norm)
    cb["valuation_musd"] = cb["valuation_busd"] * 1000

    merged = cb.copy()
    merged["forbes_list"] = None
    if frames:
        forbes = pd.concat(frames, ignore_index=True)
        fmap = forbes.drop_duplicates("key").set_index("key")
        hit = merged["key"].map(fmap["list"])
        merged["forbes_list"] = hit
        # fill missing country/industry from Forbes where CB lacks them
        missing = merged["country"].isna() | (merged["country"] == "")
        merged.loc[missing, "country"] = merged.loc[missing, "key"].map(fmap["country"])

        only_forbes = forbes[~forbes["key"].isin(merged["key"])]
        only_forbes = only_forbes.assign(forbes_list=only_forbes["list"],
                                         valuation_musd=only_forbes["valuation_musd"])
        extra = only_forbes[["company", "country", "industry", "valuation_musd",
                             "forbes_list"]]
        merged = pd.concat([merged, extra], ignore_index=True)

    merged["valuation_busd"] = merged["valuation_musd"] / 1000
    out_cols = ["company", "valuation_busd", "country", "city", "industry",
                "date_joined", "investors", "forbes_list"]
    for c in out_cols:
        if c not in merged:
            merged[c] = None
    merged = merged[out_cols].sort_values("valuation_busd", ascending=False)
    merged.to_csv(DATA / "startups_global.csv", index=False, encoding="utf-8-sig")

    print(f"merged: {len(merged)} companies")
    print(f"matched with Forbes lists: {merged.forbes_list.notna().sum()}")
    print(f"countries: {merged.country.nunique()}")
    print(merged.head(12)[["company", "valuation_busd", "country", "industry"]]
          .to_string(index=False))
    print("\ntop countries by count:")
    print(merged.country.value_counts().head(10).to_string())
    print("\ntop industries:")
    print(merged.industry.value_counts().head(10).to_string())


if __name__ == "__main__":
    main()
