"""Module 5 -- Capital: what the market thinks these firms are worth.

Three separate questions get mixed up all the time, so this module keeps
them apart:

1. **How much is listed, and how concentrated is it?** The 12,512-company
   listed universe and the 60 exchanges it trades on.
2. **What multiples do the market pay?** Price-to-sales and price-to-
   earnings by sector and by country, plus the elasticity of market value
   to revenue.
3. **How deep is each country's capital market?** Market capitalisation as
   a multiple of GDP -- the classic measure of financial depth.

A standing caveat: Forbes market values are a May 2025 snapshot while the
Fortune pages we mined were re-rendered in September 2026. They are never
added or plotted together as if they were the same vintage.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import models
import stats

KEY = "capital"

GDP_IND = "NY.GDP.MKTP.CD"


def run(ctx) -> dict:
    listed = ctx.listed().copy()
    forbes = ctx.forbes().copy()
    exchanges = ctx.bundle.get("exchanges")
    metrics: dict = {}

    listed["revenue_usd"] = pd.to_numeric(listed.get("revenue_usd"), errors="coerce")
    listed["market_cap_usd"] = pd.to_numeric(listed.get("market_cap_usd"), errors="coerce")
    listed["profit_usd"] = pd.to_numeric(listed.get("profit_usd"), errors="coerce")
    listed = listed[listed["market_cap_usd"] > 0]

    # -- 1. the listed universe -------------------------------------------
    mcap = listed["market_cap_usd"]
    metrics["listed"] = {
        "companies": int(len(listed)),
        "with_revenue": int(listed["revenue_usd"].notna().sum()),
        "total_market_cap": float(mcap.sum()),
        "median_market_cap": float(mcap.median()),
        "hhi": stats.hhi_points(mcap),
        "gini": stats.gini(mcap),
        "top10_share": stats.top_k_share(mcap, 10),
        "top100_share": stats.top_k_share(mcap, 100),
        "top500_share": stats.top_k_share(mcap, 500),
        "top1000_share": stats.top_k_share(mcap, 1000),
        "firms_for_50pct": stats.firms_for_share(mcap, 0.50),
        "firms_for_90pct": stats.firms_for_share(mcap, 0.90),
        "distribution": stats.describe(mcap),
    }

    # -- 2. exchanges -------------------------------------------------------
    ex = pd.DataFrame()
    if exchanges is not None and len(exchanges):
        ex = exchanges.copy()
        ex["total_market_cap_usd"] = pd.to_numeric(
            ex.get("total_market_cap_usd"), errors="coerce")
        ex["top10_market_cap_usd"] = pd.to_numeric(
            ex.get("top10_market_cap_usd"), errors="coerce")
        ex["companies"] = pd.to_numeric(ex.get("companies"), errors="coerce")
        ex["top10_share"] = ex["top10_market_cap_usd"] / ex["total_market_cap_usd"]
        ex["avg_company_cap"] = ex["total_market_cap_usd"] / ex["companies"].replace(0, np.nan)
        total = ex["total_market_cap_usd"].sum()
        ex["share_of_listed_total"] = ex["total_market_cap_usd"] / total
        metrics["exchanges"] = {
            "count": int(len(ex)),
            "total_market_cap": float(total),
            "note": "exchange totals cover the listed universe we can measure; "
                    "they are not a world market-capitalisation total",
            "top10": ex.nlargest(12, "total_market_cap_usd")[
                ["exchange", "exchange_country", "companies",
                 "total_market_cap_usd", "top10_market_cap_usd", "top10_share",
                 "top_company", "top_company_mcap"]].to_dict("records"),
            "most_concentrated": ex.nlargest(10, "top10_share")[
                ["exchange", "exchange_country", "companies",
                 "total_market_cap_usd", "top10_share"]].to_dict("records"),
        }
    else:
        metrics["exchanges"] = {}

    # -- 3. multiples -------------------------------------------------------
    d = listed.dropna(subset=["revenue_usd"]).copy()
    d = d[d["revenue_usd"] > 0]
    d["ps"] = d["market_cap_usd"] / d["revenue_usd"]
    d = d.assign(sector=d["sector"].fillna("Unknown"))
    metrics["multiples_by_sector"] = (
        d.groupby("sector")
        .agg(firms=("company", "count"),
             median_ps=("ps", "median"),
             p25_ps=("ps", lambda s: s.quantile(0.25)),
             p75_ps=("ps", lambda s: s.quantile(0.75)),
             total_market_cap=("market_cap_usd", "sum"),
             total_revenue=("revenue_usd", "sum"))
        .reset_index()
        .sort_values("median_ps", ascending=False)
        .to_dict("records"))

    # Price/earnings for the Forbes firms, which carry both fields.
    fp = forbes.dropna(subset=["market_cap_usd", "profit_usd"]).copy()
    fp = fp[fp["profit_usd"] > 0]
    fp["pe"] = fp["market_cap_usd"] / fp["profit_usd"]
    metrics["pe"] = {
        "firms_with_positive_profit": int(len(fp)),
        "median_pe": float(fp["pe"].median()),
        "median_pe_by_sector": fp.groupby("sector")["pe"].median()
        .sort_values(ascending=False).to_dict(),
        "top10_pe": fp.nlargest(10, "pe")[
            ["company", "country", "sector", "pe", "market_cap_usd"]].to_dict("records"),
    }

    # -- 4. elasticity of market value to revenue --------------------------
    el = models.log_log_elasticity(
        d, y="market_cap_usd", x="revenue_usd")
    metrics["valuation_elasticity"] = el
    el_profit = models.log_log_elasticity(
        forbes.dropna(subset=["profit_usd", "market_cap_usd"]).query("profit_usd > 0"),
        y="market_cap_usd", x="profit_usd")
    metrics["profit_elasticity"] = el_profit

    # -- 5. profit pool vs market value ------------------------------------
    ps = forbes.dropna(subset=["sector"]).copy()
    pool = ps.groupby("sector").agg(
        revenue=("revenue_usd", "sum"),
        profit=("profit_usd", "sum"),
        market_cap=("market_cap_usd", "sum"),
    ).reset_index()
    pool = pool.dropna()
    pool["profit_share"] = pool["profit"] / pool["profit"].sum()
    pool["market_cap_share"] = pool["market_cap"] / pool["market_cap"].sum()
    pool["profit_minus_mcap_pp"] = (pool["profit_share"] - pool["market_cap_share"]) * 100
    pool["market_cap_to_profit"] = pool["market_cap"] / pool["profit"].replace(0, np.nan)
    metrics["profit_pool_vs_market_cap"] = pool.sort_values(
        "profit_share", ascending=False).to_dict("records")

    # -- 6. financial depth by country -------------------------------------
    macro = ctx.macro_latest()
    listed_country = (listed.groupby("country")
                      .agg(market_cap=("market_cap_usd", "sum"),
                           companies=("company", "count"))
                      .reset_index())
    depth = listed_country.copy()
    if len(macro) and GDP_IND in macro.columns:
        macro_map = macro[["iso3", GDP_IND]].dropna().set_index("iso3")[GDP_IND].to_dict()
        depth["iso3"] = depth["country"].map(
            lambda c: ctx.iso(c) or "")
        depth["gdp"] = depth["iso3"].map(macro_map)
        depth["mcap_to_gdp"] = depth["market_cap"] / depth["gdp"].replace(0, np.nan)
        depth = depth.dropna(subset=["mcap_to_gdp"])
    metrics["financial_depth"] = depth.sort_values(
        "mcap_to_gdp", ascending=False).to_dict("records")

    # Financial depth is only meaningful for economies large enough to host a
    # real equity market. Micro-states (Bermuda, Cayman, BVI...) show absurd
    # ratios because a handful of multinationals are *domiciled* there, not
    # listed there. Require a >=$100B economy and a >=5-company market.
    if "gdp" in depth.columns:
        meaningful = depth[(depth["gdp"] >= 1e11) & (depth["companies"] >= 5)]
    else:
        meaningful = depth
    metrics["financial_depth_meaningful"] = meaningful.sort_values(
        "mcap_to_gdp", ascending=False).to_dict("records")
    metrics["financial_depth_excluded"] = {
        "rule": "economy with GDP >= $100B and >= 5 listed companies",
        "excluded_countries": sorted(
            set(depth["country"]) - set(meaningful["country"])),
    }

    tables = {
        "exchanges": (ex.sort_values("total_market_cap_usd", ascending=False)
                      if exchanges is not None and len(exchanges)
                      else pd.DataFrame()),
        "multiples_by_sector": pd.DataFrame(metrics["multiples_by_sector"]),
        "profit_pool": pool,
        "financial_depth": depth,
        "top_listed": listed.nlargest(100, "market_cap_usd")[
            ["company", "country", "sector", "market_cap_usd", "revenue_usd",
             "revenue_basis"]].copy(),
    }

    return {"key": KEY, "metrics": metrics, "tables": tables}


def _microstate_note(m: dict) -> str:
    """One sentence explaining what the financial-depth filter removed."""
    ex = m.get("financial_depth_excluded", {})
    names = ex.get("excluded_countries", [])
    if not names:
        return ""
    shown = ", ".join(names[:6]) + ("..." if len(names) > 6 else "")
    return (f"({len(names)} micro-state{'s' if len(names) != 1 else ''} "
            f"({shown}) are excluded: they host a handful of multinational "
            f"registrations, not a genuine domestic market.)")


def insights(m: dict) -> list[str]:
    L = m["listed"]
    fd = m.get("financial_depth_meaningful") or m.get("financial_depth") or []
    out = [
        f"The listed universe we can measure holds **{L['companies']:,}** companies worth "
        f"**${L['total_market_cap'] / 1e12:.1f} T$**. That is extraordinarily concentrated: "
        f"the top 10 hold **{L['top10_share'] * 100:.1f}%**, the top 100 "
        f"**{L['top100_share'] * 100:.1f}%**, and it takes only "
        f"**{L['firms_for_50pct']:,}** companies to reach half the total. "
        f"HHI **{L['hhi']:.0f}**, Gini **{L['gini']:.2f}**.",

        f"The median listed company is worth **${L['median_market_cap'] / 1e6:.1f}M** "
        f"while the average is **${L['total_market_cap'] / max(L['companies'], 1) / 1e6:.1f}M** "
        f"-- a **{(L['total_market_cap'] / max(L['companies'], 1)) / max(L['median_market_cap'], 1):.0f}x** "
        f"gap. The top 1,000 firms "
        f"({1000 / max(L['companies'], 1) * 100:.1f}% of the universe) alone hold "
        f"**{L['top1000_share'] * 100:.1f}%** of all measured market value.",
    ]

    if fd:
        out.append(
            f"Financial depth varies by an order of magnitude. Among economies large "
            f"enough to host a real equity market "
            f"({m.get('financial_depth_excluded', {}).get('rule', 'meaningful economies')}), "
            f"the deepest market is **{fd[0]['mcap_to_gdp']:.2f}x** GDP "
            f"({fd[0]['country']}) and the shallowest **{fd[-1]['mcap_to_gdp']:.2f}x** "
            f"({fd[-1]['country']}). "
            f"{_microstate_note(m)}")

    el = m.get("valuation_elasticity", {})
    if el.get("ok"):
        e = float(el["elasticity"])
        if e < 1:
            tail = (f"Because the elasticity is below 1, doubling revenue multiplies "
                    f"market value by about **{2 ** e:.2f}x**, not 2x -- scale by itself "
                    f"does not earn a higher valuation multiple, because the "
                    f"price-to-sales multiple shrinks as revenue grows.")
        else:
            tail = (f"Doubling revenue multiplies market value by about "
                    f"**{2 ** e:.2f}x** -- scale is rewarded at a "
                    f"{'premium' if e > 1 else 'discount'} to the size of the "
                    f"revenue base.")
        out.append(
            f"Market value scales with revenue with an elasticity of "
            f"**{e:.2f}** (95% CI "
            f"[{el['ci_low']:.2f}, {el['ci_high']:.2f}], p = {stats.fmt_p(el['p'])}; "
            f"n = {el['n']:,}). {tail}")

    pool = m.get("profit_pool_vs_market_cap", [])
    if pool:
        over = [r for r in pool if r["profit_minus_mcap_pp"] > 1.5][:3]
        under = sorted(pool, key=lambda r: r["profit_minus_mcap_pp"])[:3]
        out.append(
            "Profit and market value disagree about which businesses matter. "
            + "; ".join(f"**{r['sector']}** earns {r['profit_share'] * 100:.1f}% of profit "
                        f"but is only {r['market_cap_share'] * 100:.1f}% of market value"
                        for r in over)
            + ". Conversely "
            + "; ".join(f"**{r['sector']}** ({r['profit_minus_mcap_pp']:+.1f} pp)"
                        for r in under) + ".")
    return out
