"""Fetch the macro frame: how big the whole earth economy is, and how it splits.

Source: World Bank Open Data API (CC BY 4.0).
Outputs:
  data/world_macro.csv       long format: indicator, year, value (World aggregate)
  data/country_gdp_2024.csv  GDP by country, latest available year
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

BASE = "https://api.worldbank.org/v2"
UA = "Mozilla/5.0 (research; contact: local)"
OUT = Path("data")

INDICATORS = {
    "NY.GDP.MKTP.CD": "GDP, current US$",
    "NV.AGR.TOTL.ZS": "Agriculture, value added (% of GDP)",
    "NV.IND.TOTL.ZS": "Industry, value added (% of GDP)",
    "NV.SRV.TOTL.ZS": "Services, value added (% of GDP)",
    "NV.IND.MANF.ZS": "Manufacturing, value added (% of GDP)",
    "SL.AGR.EMPL.ZS": "Employment in agriculture (% of total employment)",
    "SL.IND.EMPL.ZS": "Employment in industry (% of total employment)",
    "SL.SRV.EMPL.ZS": "Employment in services (% of total employment)",
    "SL.TLF.TOTL.IN": "Labor force, total",
    "SP.POP.TOTL": "Population, total",
    "CM.MKT.LDOM.NO": "Listed domestic companies, total",
}


def get(url: str, params: dict, tries: int = 4):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=60)
            r.raise_for_status()
            return r.json()
        except Exception as exc:  # noqa: BLE001
            print(f"  retry {i+1}/{tries}: {exc}")
            time.sleep(2 * (i + 1))
    return None


def main() -> None:
    rows = []
    for code, label in INDICATORS.items():
        data = get(f"{BASE}/country/WLD/indicator/{code}",
                   {"format": "json", "date": "2000:2024", "per_page": 100})
        if not data or len(data) < 2 or not data[1]:
            print(f"  no data for {code}")
            continue
        for rec in data[1]:
            if rec.get("value") is None:
                continue
            rows.append({"indicator": code, "indicator_name": label,
                         "year": int(rec["date"]), "value": float(rec["value"])})
        print(f"  {code}: {len(data[1])} obs")

    df = pd.DataFrame(rows).sort_values(["indicator", "year"])
    df.to_csv(OUT / "world_macro.csv", index=False, encoding="utf-8-sig")
    print(f"wrote world_macro.csv rows={len(df)}")

    # country GDP, latest year per country (paginate: >500 records)
    recs = []
    page = 1
    while True:
        data = get(f"{BASE}/country/all/indicator/NY.GDP.MKTP.CD",
                   {"format": "json", "date": "2023:2024", "per_page": 500, "page": page})
        if not data or len(data) < 2:
            break
        for rec in data[1]:
            if rec.get("value") is None:
                continue
            iso = rec.get("countryiso3code") or ""
            if len(iso) != 3:
                continue
            recs.append({"country": rec["country"]["value"], "iso3": iso,
                         "year": int(rec["date"]), "gdp_usd": float(rec["value"])})
        if page >= data[0].get("pages", 1):
            break
        page += 1
        time.sleep(0.3)

    if recs:
        meta = get(f"{BASE}/country", {"format": "json", "per_page": 400})
        mdf = pd.DataFrame([
            {"iso3": m["id"], "name": m["name"], "region": m["region"]["value"]}
            for m in (meta[1] if meta and len(meta) > 1 else [])
        ])
        mdf = mdf[mdf["region"] != "Aggregates"]
        mdf.to_csv(OUT / "country_meta.csv", index=False, encoding="utf-8-sig")

        cdf = (pd.DataFrame(recs)
                 .sort_values("year", ascending=False)
                 .drop_duplicates("iso3")
                 .merge(mdf[["iso3", "name"]], on="iso3", how="inner")
                 .drop(columns=["country"])
                 .rename(columns={"name": "country"})
                 .sort_values("gdp_usd", ascending=False))
        cdf.to_csv(OUT / "country_gdp_2024.csv", index=False, encoding="utf-8-sig")
        print(f"wrote country_gdp_2024.csv rows={len(cdf)}")


if __name__ == "__main__":
    main()
