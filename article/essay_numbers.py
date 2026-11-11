"""Every Forbes-based number quoted in the essay, computed from one list year.

Run from the repo root:  python article/essay_numbers.py [year]   (default 2026)
Writes article/data/essay_numbers_<year>.json and prints a readable summary.
Numbers that come from other sources (World Bank, ILO, CB Insights, Crunchbase,
EY, Fortune ownership labels) are read from the same files the site uses.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
EU27 = {"Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic", "Denmark", "Estonia",
        "Finland", "France", "Germany", "Greece", "Hungary", "Ireland", "Italy", "Latvia", "Lithuania",
        "Luxembourg", "Malta", "Netherlands", "Poland", "Portugal", "Romania", "Slovakia", "Slovenia",
        "Spain", "Sweden"}


def site(page: str) -> dict:
    """Read a site data file (window.ATLAS.<page> = {...};)."""
    t = (ROOT / f"site/data/{page}.js").read_text(encoding="utf-8")
    return json.loads(t[t.index("= ", t.index(f"ATLAS.{page}")) + 2:].rstrip().rstrip(";"))


def half(s: pd.Series) -> int:
    s = s.clip(lower=0).sort_values(ascending=False)
    return int((s.cumsum() < s.sum() / 2).sum() + 1)


def main() -> None:
    g = pd.read_csv(ROOT / f"data/global2000_{YEAR}.csv", encoding="utf-8-sig")
    gdp = pd.read_csv(ROOT / "data/country_gdp_2024.csv", encoding="utf-8-sig")
    macro = site("sectors")["economy"]
    world_gdp, workers = macro["gdp_usd"], macro["labour_force"]
    rev, pro, mv = g.revenue_musd, g.profits_musd, g.market_value_musd
    N = {}

    N["totals"] = dict(rev_T=rev.sum() / 1e6, profit_T=pro.sum() / 1e6, mv_T=mv.sum() / 1e6,
                       employees_M=g.employees.sum() / 1e6, loss_makers=int((pro < 0).sum()))
    N["rev_pct_world_gdp"] = 100 * rev.sum() * 1e6 / world_gdp
    N["worker_share_pct"] = 100 * g.employees.sum() / workers
    N["one_worker_in"] = workers / g.employees.sum()
    N["half_of"] = dict(revenue=half(rev), profit=half(pro), market_value=half(mv))
    N["share_of_listed_pct"] = 100 * 2000 / 47_980

    # Sectors: shares and valuation
    sec = g.groupby("sector").agg(n=("company", "size"), rev=("revenue_musd", "sum"),
                                  pro=("profits_musd", "sum"), mv=("market_value_musd", "sum"))
    sec["rev_pct"] = 100 * sec.rev / sec.rev.sum()
    sec["pro_pct"] = 100 * sec.pro / sec.pro.sum()
    sec["mv_pct"] = 100 * sec.mv / sec.mv.sum()
    pos = g[g.profits_musd > 0].groupby("sector").profits_musd.sum()
    sec["pe"] = sec.mv / pos
    sec["n_100B"] = g[rev >= 100_000].groupby("sector").size()
    sec = sec.fillna({"n_100B": 0}).sort_values("rev", ascending=False)
    N["sectors"] = sec.round(2).reset_index().to_dict("records")

    # Countries
    def ctry(mask):
        x = g[mask]
        return dict(n=len(x), rev_pct=100 * x.revenue_musd.sum() / rev.sum(),
                    pro_pct=100 * x.profits_musd.sum() / pro.sum(),
                    mv_pct=100 * x.market_value_musd.sum() / mv.sum(),
                    avg_rev_B=x.revenue_musd.mean() / 1e3)
    us = ctry(g.country == "United States")
    us["gdp_pct"] = 100 * gdp.loc[gdp.iso3 == "USA", "gdp_usd"].iloc[0] / world_gdp
    N["us"] = us
    N["china"] = ctry(g.country == "China")
    N["japan"] = ctry(g.country == "Japan")
    N["india"] = ctry(g.country == "India")
    N["eu27"] = ctry(g.country.isin(EU27))
    N["russia_n"] = int((g.country == "Russia").sum())
    by_n = g.country.value_counts()
    by_rev = g.groupby("country").revenue_musd.sum().sort_values(ascending=False)
    N["india"]["rank_by_count"] = int(list(by_n.index).index("India") + 1)
    N["india"]["rank_by_revenue"] = int(list(by_rev.index).index("India") + 1)

    # Country business DNA (revenue mix by sector)
    def mix(mask):
        x = g[mask]
        return (100 * x.groupby("sector").revenue_musd.sum() / x.revenue_musd.sum()).round(1).to_dict()
    N["dna"] = {"World": mix(g.country.notna()), "United States": mix(g.country == "United States"),
                "China": mix(g.country == "China"), "Japan": mix(g.country == "Japan"),
                "India": mix(g.country == "India"), "Germany": mix(g.country == "Germany"),
                "Gulf": mix(g.country.isin(["Saudi Arabia", "United Arab Emirates", "Qatar", "Kuwait"]))}

    # Unicorns (CB Insights snapshot, as on the site)
    geo = site("geography")
    usd = next(c for c in geo["countries"] if c["name"] == "United States")
    N["us"]["unicorn_value_pct"] = 100 * usd["u_val"] / geo["world"]["u_val"]
    eu_u = sum(c.get("u_val") or 0 for c in geo["countries"] if c["name"] in EU27)
    N["eu27"]["unicorn_value_pct"] = 100 * eu_u / geo["world"]["u_val"]
    N["eu27"]["gdp_pct"] = 100 * gdp[gdp.country.isin(EU27)].gdp_usd.sum() / world_gdp
    N["eu27"]["unicorns"] = sum(c.get("u_n") or 0 for c in geo["countries"] if c["name"] in EU27)
    N["japan"]["unicorns"] = next(c for c in geo["countries"] if c["name"] == "Japan").get("u_n")

    # Company vs country, decade change, ownership: as computed on the site
    sc = site("scale")
    N["company_vs_country"] = sc["vivid"]
    N["trillion_club"] = dict(n=len(sc["trillion"]), us=sum(t["c"] == "United States" for t in sc["trillion"]))
    N["true_top15"] = [dict(name=t["n"], owner=t["o"], rev_B=t["rev"]) for t in sc["true_top"][:15]]
    tm = site("time")
    N["decade"] = dict(tm["H"], years=[tm["years"][0], tm["years"][-1]])
    bumps = {b["company"]: b["rank"] for b in tm["bumps"]["rev"]}
    N["decade"]["rank_moves"] = {k: [v[0], v[-1]] for k, v in bumps.items()}
    nv = next(m for m in tm["movers"]["all"] if m["company"] == "NVIDIA")
    N["decade"]["nvidia"] = dict(rev_start_B=nv["rev15"] / 1e3, rev_end_B=nv["rev24"] / 1e3,
                                 multiple=nv["rev24"] / nv["rev15"])
    ow = site("ownership")
    N["ownership"] = dict(ow["H"], fortune_mix=ow["fortune_mix"], india_stats=ow["india_stats"])

    out = ROOT / f"article/data/essay_numbers_{YEAR}.json"
    out.write_text(json.dumps(N, indent=1, default=float), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}")
    t = N["totals"]
    print(f"Totals: rev ${t['rev_T']:.1f}T, profit ${t['profit_T']:.2f}T, MV ${t['mv_T']:.1f}T, "
          f"{t['employees_M']:.1f}M staff, {t['loss_makers']} loss-makers")
    print(f"Revenue = {N['rev_pct_world_gdp']:.1f}% of world GDP; staff = {N['worker_share_pct']:.1f}% of workers "
          f"(1 in {N['one_worker_in']:.0f}); half: {N['half_of']}")
    print("US:", {k: round(v, 1) for k, v in N["us"].items()})
    print("EU27:", {k: round(v, 1) for k, v in N["eu27"].items()}, "| Japan:", N["japan"]["n"], "giants,",
          N["japan"]["unicorns"], "unicorns | Russia firms:", N["russia_n"])
    print("India:", {k: round(v, 1) for k, v in N["india"].items()})
    print("Sectors:")
    for s in N["sectors"]:
        print(f"  {s['sector']:<27} n={s['n']:<4} rev {s['rev_pct']:5.1f}%  pro {s['pro_pct']:5.1f}%  "
              f"mv {s['mv_pct']:5.1f}%  P/E {s['pe']:5.1f}  $100B+ {int(s['n_100B'])}")
    for k, v in N["dna"].items():
        top = sorted(v.items(), key=lambda kv: -kv[1])[:3]
        print(f"  DNA {k}: {top}")
    print("Decade:", {k: v for k, v in N["decade"].items() if k != "rank_moves"})
    print("Rank moves:", {k: v for k, v in N["decade"]["rank_moves"].items()
                          if k in ("Amazon", "Walmart", "Alphabet", "Microsoft", "Shell Plc", "Apple")})
    print("Trillion club:", N["trillion_club"])
    print("Vivid:", [(v["label"], v["rank"], v["n_smaller"]) for v in N["company_vs_country"][:4]])


if __name__ == "__main__":
    main()
