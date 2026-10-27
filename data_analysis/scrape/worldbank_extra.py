"""Build a proper country-year macro panel from the World Bank API.

The ``data/world_macro.csv`` file that ships with the project is thin: it
holds a handful of world aggregates rather than a country panel. For the
geography analysis we need, per country and per year, the denominator series
that let us ask "is this country over- or under-represented in the Fortune
500 relative to its economic weight?".

Indicators pulled (all World Bank, open API, no key required):

  NY.GDP.MKTP.CD    GDP, current US$              -> economy size
  NY.GDP.PCAP.CD    GDP per capita, current US$    -> wealth
  NY.GDP.MKTP.PP.CD GDP, PPP (current int. US$)    -> real size
  NY.GDP.PCAP.PP.CD GDP per capita, PPP             -> real wealth
  SP.POP.TOTL       Population, total              -> scale of the workforce
  SL.TLF.TOTL.IN    Labor force, total              -> workers
  SL.EMP.TOTL.SP.ZS Employment to population ratio -> labour participation
  SL.UEM.TOTL.ZS    Unemployment, % of labour force
  SL.AGR.EMPL.ZS    Employment in agriculture      -> labour share
  SL.IND.EMPL.ZS    Employment in industry
  SL.SRV.EMPL.ZS    Employment in services
  NV.AGR.TOTL.ZS    Agriculture, value added % GDP -> value added share
  NV.IND.TOTL.ZS    Industry, value added % GDP
  NV.SRV.TOTL.ZS    Services, value added % GDP
  NV.IND.MANF.ZS    Manufacturing, value added % GDP
  NE.TRD.GNFS.ZS    Trade, % of GDP                 -> openness
  BX.KLT.DINV.WD.GD.ZS  FDI net inflows, % of GDP  -> capital attraction
  CM.MKT.LDOM.NO   Listed domestic companies       -> depth of capital markets
  SP.DYN.TFRT.IN    Fertility rate, total

Output: ``output/raw/worldbank_extra.csv`` (long format:
iso3, country, indicator, indicator_name, year, value)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import requests

from config import OUT_RAW

API = "https://api.worldbank.org/v2"

INDICATORS: dict[str, str] = {
    "NY.GDP.MKTP.CD": "GDP, current US$",
    "NY.GDP.PCAP.CD": "GDP per capita, current US$",
    "NY.GDP.MKTP.PP.CD": "GDP, PPP (current international US$)",
    "NY.GDP.PCAP.PP.CD": "GDP per capita, PPP (current international US$)",
    "SP.POP.TOTL": "Population, total",
    "SL.TLF.TOTL.IN": "Labor force, total",
    "SL.EMP.TOTL.SP.ZS": "Employment to population ratio, 15+, total (%)",
    "SL.UEM.TOTL.ZS": "Unemployment, total (% of total labor force)",
    "SL.AGR.EMPL.ZS": "Employment in agriculture (% of total employment)",
    "SL.IND.EMPL.ZS": "Employment in industry (% of total employment)",
    "SL.SRV.EMPL.ZS": "Employment in services (% of total employment)",
    "NV.AGR.TOTL.ZS": "Agriculture, value added (% of GDP)",
    "NV.IND.TOTL.ZS": "Industry, value added (% of GDP)",
    "NV.SRV.TOTL.ZS": "Services, value added (% of GDP)",
    "NV.IND.MANF.ZS": "Manufacturing, value added (% of GDP)",
    "NE.TRD.GNFS.ZS": "Trade (% of GDP)",
    "BX.KLT.DINV.WD.GD.ZS": "FDI, net inflows (% of GDP)",
    "CM.MKT.LDOM.NO": "Listed domestic companies, total",
    "SP.DYN.TFRT.IN": "Fertility rate, total (births per woman)",
}

YEAR_FROM, YEAR_TO = 2000, 2024


def fetch_indicator(code: str, session: requests.Session) -> pd.DataFrame:
    rows: list[dict] = []
    page = 1
    while True:
        url = f"{API}/country/all/indicator/{code}"
        params = {"format": "json", "per_page": 20000, "date": f"{YEAR_FROM}:{YEAR_TO}",
                  "page": page}
        for attempt in range(4):
            r = session.get(url, params=params, timeout=90)
            if r.status_code == 200:
                break
            time.sleep(4 * (attempt + 1))
        else:
            return pd.DataFrame(rows)

        payload = r.json()
        if not isinstance(payload, list) or len(payload) < 2:
            break
        meta, data = payload[0], payload[1]
        for rec in data:
            if rec.get("value") is None:
                continue
            iso3 = rec.get("countryiso3code")
            if not iso3:
                continue
            rows.append({
                "iso3": iso3,
                "country": rec.get("country", {}).get("value", ""),
                "indicator": code,
                "indicator_name": INDICATORS.get(code, ""),
                "year": int(rec["date"]),
                "value": float(rec["value"]),
            })
        pages = int(meta.get("pages", 1))
        page += 1
        if page > pages:
            break
        time.sleep(0.6)
    return pd.DataFrame(rows)


def main() -> pd.DataFrame:
    session = requests.Session()
    session.headers["User-Agent"] = "company-data-analysis/1.0 (research script)"

    frames = []
    for i, code in enumerate(INDICATORS, 1):
        df = fetch_indicator(code, session)
        frames.append(df)
        print(f"[{i:>2}/{len(INDICATORS)}] {code:<24} rows={len(df):>7,}")

    all_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if len(all_df):
        all_df = all_df.drop_duplicates(subset=["iso3", "indicator", "year"])
        all_df = all_df.sort_values(["indicator", "iso3", "year"])

    OUT_RAW.mkdir(parents=True, exist_ok=True)
    path = OUT_RAW / "worldbank_extra.csv"
    all_df.to_csv(path, index=False, encoding="utf-8")
    if len(all_df):
        print(f"\nrows {len(all_df):,}  countries {all_df['iso3'].nunique()}  "
              f"indicators {all_df['indicator'].nunique()}  "
              f"years {all_df['year'].min()}-{all_df['year'].max()}")
    print(f"written -> {path}")
    return all_df


if __name__ == "__main__":
    main()
