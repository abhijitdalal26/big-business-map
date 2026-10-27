"""Merge every company source into one master table with provenance.

Sources:
  - Forbes Global 2000 <year>-> public companies (the spine)
  - Fortune Global 500 <year>-> revenue-ranked, includes state-owned and private
                                companies that disclose financials
  - Forbes Cloud 100 / Next Billion-Dollar Startups -> VC-backed private

The point of the master table is not to sum revenue across sources (the methods
differ) but to see which businesses exist and how each is labelled.
"""

from __future__ import annotations

import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

# Usage: python scripts/build_master.py [year] [startups_year] [private_year]
# Defaults: year 2026; startups/private fall back to the newest earlier file that
# exists (e.g. Cloud 100 / private list not yet published for 2026 -> 2025).
YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
OUT = Path("data/companies_master.csv")


def latest(prefix: str, year: int, pin: str | None = None) -> Path:
    if pin:
        return Path(f"data/{prefix}_{pin}.csv")
    for y in range(year, 2019, -1):
        p = Path(f"data/{prefix}_{y}.csv")
        if p.exists():
            return p
    return Path(f"data/{prefix}_{year}.csv")


COUNTRY_FIX = {"U.S.": "United States", "U.K.": "United Kingdom", "Britain": "United Kingdom",
               "Mainland China": "China"}

# Fortune slugs (or names) known to be majority state-owned.
STATE_OWNED = {
    "state-grid", "china-national-petroleum", "china-railway", "china-baowu",
    "china-state-construction", "pemex", "adnoc", "qatarenergy", "kuwait-petroleum",
    "edf", "deutsche-bahn", "sncf", "saudi-aramco", "china-mobile",
    "china-southern-power-grid", "china-huaneng", "china-datang",
    "china-cosco-shipping", "china-railway-construction", "cnpc",
    "sinopec", "petrochina", "icbc", "china-construction-bank",
    "agricultural-bank-of-china", "bank-of-china",
}

SUFFIXES = {
    "inc", "corp", "corporation", "co", "company", "ltd", "limited", "plc",
    "ag", "sa", "nv", "se", "spa", "group", "holding", "holdings", "the",
}


def norm(name: str) -> str:
    s = str(name).lower().replace("&", " and ")
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    tokens = [t for t in s.split() if t and t not in SUFFIXES]
    return " ".join(tokens)


def match_fortune(name: str, forbes_names: list[str], forbes_norm: list[str]) -> int | None:
    n = norm(name)
    if not n:
        return None
    for i, fn in enumerate(forbes_norm):
        if n == fn:
            return i
    for i, fn in enumerate(forbes_norm):
        if len(n) > 3 and (n in fn or fn in n):
            return i
    best_i, best_r = None, 0.0
    for i, fn in enumerate(forbes_norm):
        r = SequenceMatcher(None, n, fn).ratio()
        if r > best_r:
            best_i, best_r = i, r
    if best_r >= 0.9:
        return best_i
    return None


def main() -> None:
    forbes = pd.read_csv(f"data/global2000_{YEAR}.csv")
    forbes["source"] = "Forbes Global 2000 (public)"
    forbes["ownership"] = "Public"
    forbes["rank_in_source"] = forbes["rank"]
    forbes["notes"] = None

    cols = ["company", "source", "ownership", "country", "sector", "industry_canon",
            "industry_raw", "revenue_musd", "profits_musd", "assets_musd",
            "market_value_musd", "employees", "rank_in_source", "notes"]
    forbes = forbes.rename(columns={"industry": "industry_raw"})[cols]

    frames = [forbes]

    fpath = Path(f"data/fortune_g500_{YEAR}.csv")
    labels = pd.read_csv("data/fortune_labels.csv").set_index("slug")
    if fpath.exists():
        fortune = pd.read_csv(fpath)
        fnames = forbes["company"].tolist()
        fnorm = [norm(n) for n in fnames]

        rows = []
        for _, r in fortune.iterrows():
            slug = str(r["slug"])
            label = labels.loc[slug] if slug in labels.index else None
            if label is not None and label["ownership"] == "DUPLICATE":
                continue
            if match_fortune(r["company"], fnames, fnorm) is not None:
                continue
            ownership = label["ownership"] if label is not None else "Unclassified"
            rows.append({
                "company": r["company"],
                "source": "Fortune Global 500 (outside Forbes 2000)",
                "ownership": ownership,
                "country": COUNTRY_FIX.get(r.get("country"), r.get("country")) if "country" in r else None,
                "sector": "Unclassified",
                "industry_canon": "Unclassified",
                "industry_raw": r.get("industry") if "industry" in r else None,
                "revenue_musd": pd.to_numeric(r["revenues_musd"], errors="coerce"),
                "profits_musd": pd.to_numeric(r["profits_musd"], errors="coerce"),
                "assets_musd": pd.to_numeric(r["assets_musd"], errors="coerce") if "assets_musd" in r else None,
                "market_value_musd": pd.to_numeric(r["market_value_musd"], errors="coerce"),
                "employees": pd.to_numeric(r["employees"], errors="coerce"),
                "rank_in_source": r["rank"],
                "notes": r["headquarters"],
            })
        extra = pd.DataFrame(rows)
        print(f"fortune rows: {len(fortune)}, duplicates removed: "
              f"{(labels['ownership'] == 'DUPLICATE').sum()}, added: {len(extra)}")
        frames.append(extra)

    ppath = latest("private_us", YEAR, sys.argv[3] if len(sys.argv) > 3 else None)
    if ppath.exists():
        from taxonomy import annotate
        pv = pd.read_csv(ppath)
        pv = annotate(pv, "industry")
        frames.append(pd.DataFrame({
            "company": pv["company"],
            "source": "Forbes Largest Private (US)",
            "ownership": "Private",
            "country": pv["country"],
            "sector": pv["sector"],
            "industry_canon": pv["industry_canon"],
            "industry_raw": pv["industry"],
            "revenue_musd": pv["revenue_musd"],
            "profits_musd": None,
            "assets_musd": None,
            "market_value_musd": None,
            "employees": pv["employees"],
            "rank_in_source": pv["rank"],
            "notes": pv["city"],
        }))

    spath = latest("startups", YEAR, sys.argv[2] if len(sys.argv) > 2 else None)
    if spath.exists():
        st = pd.read_csv(spath)
        # A list with no edition yet for this year is carried forward from the
        # newest earlier file, flagged in the source label.
        for lst in ("Cloud 100", "Next Billion-Dollar Startups"):
            if (st["list"] == lst).any():
                continue
            for y in range(YEAR - 1, 2019, -1):
                q = Path(f"data/startups_{y}.csv")
                if q.exists() and (pd.read_csv(q)["list"] == lst).any():
                    old = pd.read_csv(q)
                    old = old[old["list"] == lst].copy()
                    old["list"] = f"{lst} ({y} edition; no {YEAR} edition yet)"
                    st = pd.concat([st, old], ignore_index=True)
                    print(f"{lst}: carried forward from {y}")
                    break
        st = pd.DataFrame({
            "company": st["company"],
            "source": st["list"],
            "ownership": "Private (VC-backed)",
            "country": st["country"],
            "sector": "Technology",
            "industry_canon": "Cloud / Software",
            "industry_raw": st["industry"],
            "revenue_musd": None,
            "profits_musd": None,
            "assets_musd": None,
            "market_value_musd": st["valuation_musd"],
            "employees": st["employees"],
            "rank_in_source": st["rank"],
            "notes": st["city"],
        })
        frames.append(st)

    master = pd.concat(frames, ignore_index=True)
    for col in ("revenue_musd", "profits_musd", "assets_musd", "market_value_musd", "employees"):
        master[col] = pd.to_numeric(master[col], errors="coerce")
    master.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"\nwrote {OUT} rows={len(master)}")
    print(master.groupby(["source", "ownership"]).size().to_string())

    unlisted = master[master["source"] == "Fortune Global 500 (outside Forbes 2000)"]
    if len(unlisted):
        print(f"\noutside-Forbes revenue: ${unlisted['revenue_musd'].sum()/1e6:,.2f}T "
              f"across {len(unlisted)} companies")
        print(unlisted.groupby("ownership")["revenue_musd"].sum().div(1e6).round(2)
              .sort_values(ascending=False).to_string())
        print(unlisted.nlargest(12, "revenue_musd")[
            ["company", "ownership", "revenue_musd"]].to_string(index=False))


if __name__ == "__main__":
    main()
