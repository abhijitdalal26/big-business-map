"""Key numbers for the article, written to analysis/findings.md."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path("data/global2000_2025.csv")
HIST = Path("data/global2000_2025_history.csv")
OUT = Path("analysis/findings.md")
OUT.parent.mkdir(parents=True, exist_ok=True)


def money(x_musd: float) -> str:
    """$M -> readable string."""
    if abs(x_musd) >= 1e6:
        return f"${x_musd/1e6:,.2f}T"
    if abs(x_musd) >= 1e3:
        return f"${x_musd/1e3:,.1f}B"
    return f"${x_musd:,.0f}M"


def pct(x: float) -> str:
    return f"{x:,.1f}%"


def main() -> None:
    df = pd.read_csv(DATA)
    lines: list[str] = []
    add = lines.append

    add("# Forbes Global 2000 (2025) — key findings\n")
    add("Data: Forbes Global 2000, 2025 list (published June 2025; financials to FY2024).")
    add(f"Rows: {len(df):,}. All money in USD.\n")

    total_rev = df["revenue_musd"].sum()
    total_prof = df["profits_musd"].sum()
    total_mv = df["market_value_musd"].sum()
    total_assets = df["assets_musd"].sum()
    add("## The whole board\n")
    add(f"- Combined revenue: **{money(total_rev)}**")
    add(f"- Combined profit: **{money(total_prof)}** (net margin {pct(total_prof/total_rev*100)})")
    add(f"- Combined assets: **{money(total_assets)}**")
    add(f"- Combined market value: **{money(total_mv)}**")
    add(f"- Combined employees: **{df['employees'].sum()/1e6:,.1f} million**\n")

    # concentration
    rev_sorted = df["revenue_musd"].sort_values(ascending=False)
    add("## Concentration\n")
    for k in (10, 50, 100, 500):
        share = rev_sorted.head(k).sum() / total_rev * 100
        add(f"- Top {k} companies = **{pct(share)}** of total revenue")
    add("")

    # countries
    ctry = df.groupby("country").agg(
        n=("company", "count"),
        revenue=("revenue_musd", "sum"),
        profits=("profits_musd", "sum"),
        market_value=("market_value_musd", "sum"),
    ).sort_values("revenue", ascending=False)
    ctry["rev_share"] = ctry["revenue"] / total_rev * 100
    ctry["profit_share"] = ctry["profits"] / total_prof * 100

    add("## The country picture\n")
    add("| Country | Companies | Revenue | Rev share | Profit share |")
    add("|---|---|---|---|---|")
    for name, row in ctry.head(15).iterrows():
        add(f"| {name} | {int(row.n):,} | {money(row.revenue)} | {pct(row.rev_share)} | {pct(row.profit_share)} |")
    add("")

    us = ctry.loc["United States"]
    cn = ctry.loc["China"]
    add(f"- US: {int(us.n)} companies, {pct(us.rev_share)} of revenue, {pct(us.profit_share)} of profit.")
    add(f"- China: {int(cn.n)} companies, {pct(cn.rev_share)} of revenue, {pct(cn.profit_share)} of profit.")
    add(f"- US companies earn **{us.profits/us.revenue*100:,.1f}%** net margin; Chinese companies **{cn.profits/cn.revenue*100:,.1f}%**.\n")

    # regions
    reg = df.groupby("region").agg(n=("company", "count"), revenue=("revenue_musd", "sum"),
                                   profits=("profits_musd", "sum"))
    reg["rev_share"] = reg["revenue"] / total_rev * 100
    add("## By region\n")
    add("| Region | Companies | Revenue | Rev share |")
    add("|---|---|---|---|")
    for name, row in reg.sort_values("revenue", ascending=False).iterrows():
        add(f"| {name} | {int(row.n):,} | {money(row.revenue)} | {pct(row.rev_share)} |")
    add("")

    # industries
    ind = df.groupby("industry").agg(
        n=("company", "count"),
        revenue=("revenue_musd", "sum"),
        profits=("profits_musd", "sum"),
    )
    ind["rev_share"] = ind["revenue"] / total_rev * 100
    ind["profit_share"] = ind["profits"] / total_prof * 100
    ind["margin"] = ind["profits"] / ind["revenue"] * 100

    add("## Industry profit pools\n")
    add("| Industry | Companies | Revenue | Profit | Profit share | Net margin |")
    add("|---|---|---|---|---|---|")
    for name, row in ind.sort_values("profits", ascending=False).head(15).iterrows():
        add(f"| {name} | {int(row.n)} | {money(row.revenue)} | {money(row.profits)} | {pct(row.profit_share)} | {pct(row.margin)} |")
    add("")

    add("Biggest profit pools (% of all profit):")
    for name, row in ind.sort_values("profits", ascending=False).head(8).iterrows():
        add(f"- {name}: **{pct(row.profit_share)}** ({money(row.profits)})")
    add("")

    # extremes
    add("## Extremes\n")
    top_rev = df.nlargest(5, "revenue_musd")[["company", "country", "revenue_musd"]]
    add("Largest by revenue:")
    for _, r in top_rev.iterrows():
        add(f"- {r.company} ({r.country}): {money(r.revenue_musd)}")
    top_mv = df.nlargest(5, "market_value_musd")[["company", "country", "market_value_musd"]]
    add("\nLargest by market value:")
    for _, r in top_mv.iterrows():
        add(f"- {r.company} ({r.country}): {money(r.market_value_musd)}")
    add("")

    best = df[(df["revenue_musd"] > 1000) & (df["profit_margin_pct"].between(0, 80))]
    best = best.nlargest(8, "profit_margin_pct")[["company", "industry", "profit_margin_pct", "revenue_musd"]]
    add("Highest net margins (revenue > $1B, margin capped at 80% to exclude holding-company flukes):")
    for _, r in best.iterrows():
        add(f"- {r.company} ({r.industry}): {r.profit_margin_pct:.1f}% on {money(r.revenue_musd)} revenue")
    add(f"\nCompanies reporting a loss: **{(df['profits_musd'] < 0).sum()}** "
        f"({(df['profits_musd'] < 0).mean()*100:.1f}% of the list).\n")

    # history: constant cohort = companies present in the oldest year
    hist = pd.read_csv(HIST)
    rev_h = hist[hist.metric == "revenue"]
    oldest = int(rev_h["years_ago"].max())
    cohort = set(rev_h.loc[rev_h["years_ago"] == oldest, "company"])
    rev_h = rev_h[rev_h["company"].isin(cohort)]
    agg = rev_h.groupby("years_ago").agg(total=("value", "sum"), n=("value", "count")).sort_index()
    base = agg.loc[0, "total"]
    add("## The ten-year trend (constant cohort: the "
        f"{len(cohort):,} companies that report all {oldest+1} years)\n")
    add("| Years ago | Approx FY | Companies reporting | Revenue | vs latest |")
    add("|---|---|---|---|---|")
    for ya, row in agg.iterrows():
        add(f"| {int(ya)} | {2024-int(ya)} | {int(row.n):,} | {money(row.total)} | {row.total/base*100:.0f}% |")
    cagr = (base / agg.loc[agg.index.max(), "total"]) ** (1 / agg.index.max()) - 1
    add(f"\nImplied CAGR of this cohort's revenue: **{cagr*100:,.1f}%** per year.\n")

    # profit history
    p_h = hist[(hist.metric == "profits") & (hist.company.isin(cohort))]
    p_h = p_h.groupby("years_ago")["value"].sum().sort_index()
    add(f"Profits ten years ago (same cohort): {money(p_h.loc[p_h.index.max()])} vs {money(p_h.loc[0])} now "
        f"(x{p_h.loc[0]/p_h.loc[p_h.index.max()]:,.2f}).\n")

    add("## Caveats\n")
    add("- Forbes figures are trailing-twelve-month estimates at the list's compilation date; they are not")
    add("  audited filings and differ from company-reported GAAP figures.")
    add("- Market values are a snapshot (May 2025), not a live price. The 2025 list's market values predate")
    add("  later rallies, so today's caps are higher for several tech names.")
    add("- Financial-sector revenue (banks, insurers) is not comparable to industrial revenue: bank")
    add("  'revenue' is interest + fee income, which inflates the Banking total.")
    add("- The ten-year series only covers companies on the 2025 list, so it understates true global growth")
    add("  (survivorship bias).")
    add("- China/Hong Kong are reported as separate countries by Forbes; combined they exceed Japan.")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
