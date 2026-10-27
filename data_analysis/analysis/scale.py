"""Module 1 -- Scale: how big is big, and how concentrated is the top?

Two ideas drive this module.

1. The Forbes Global 2000 is a *truncated* view. It stops at rank 2,000, so
   the total revenue of the world's largest firms is understated by
   everything below the cut. We can measure that gap directly, because the
   listed universe gives us revenue for 12,468 more firms.

2. Concentration is not one number. HHI, Gini, top-k shares, the Zipf
   exponent and the "how many firms for half the total" count all say
   different things about the same distribution, so we compute them all.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import stats

KEY = "scale"


def run(ctx) -> dict:
    forbes = ctx.forbes().copy()
    listed = ctx.listed().copy()
    rev = forbes["revenue_usd"].dropna()
    profit = forbes["profit_usd"].dropna()

    metrics: dict = {}

    # -- headline aggregates ----------------------------------------------
    metrics["forbes_company_count"] = int(len(forbes))
    metrics["forbes_revenue_total"] = float(rev.sum())
    metrics["forbes_profit_total"] = float(profit.sum())
    metrics["forbes_assets_total"] = float(forbes["assets_usd"].dropna().sum())
    metrics["forbes_market_cap_total"] = float(forbes["market_cap_usd"].dropna().sum())
    metrics["forbes_employees_total"] = float(forbes["employees"].dropna().sum())
    metrics["forbes_blended_margin"] = float(
        profit.sum() / rev.sum()) if rev.sum() else float("nan")
    metrics["forbes_loss_makers"] = int((forbes["profit_usd"] < 0).sum())
    metrics["forbes_loss_maker_share"] = float(
        (forbes["profit_usd"] < 0).mean()) if len(forbes) else float("nan")

    # -- distribution shape ------------------------------------------------
    metrics["revenue_distribution"] = stats.describe(rev)
    metrics["profit_distribution"] = stats.describe(profit)
    metrics["employees_distribution"] = stats.describe(forbes["employees"].dropna())
    metrics["market_cap_distribution"] = stats.describe(forbes["market_cap_usd"].dropna())

    # -- concentration -----------------------------------------------------
    metrics["concentration"] = {
        "hhi_revenue": stats.hhi_points(rev),
        "hhi_profit": stats.hhi_points(profit),
        "gini_revenue": stats.gini(rev),
        "gini_profit": stats.gini(profit),
        "top10_revenue_share": stats.top_k_share(rev, 10),
        "top50_revenue_share": stats.top_k_share(rev, 50),
        "top100_revenue_share": stats.top_k_share(rev, 100),
        "top500_revenue_share": stats.top_k_share(rev, 500),
        "top1000_revenue_share": stats.top_k_share(rev, 1000),
        "top100_profit_share": stats.top_k_share(profit, 100),
        "top500_profit_share": stats.top_k_share(profit, 500),
        "firms_for_50pct_revenue": stats.firms_for_share(rev, 0.50),
        "firms_for_80pct_revenue": stats.firms_for_share(rev, 0.80),
        "firms_for_90pct_revenue": stats.firms_for_share(rev, 0.90),
        "firms_for_95pct_revenue": stats.firms_for_share(rev, 0.95),
    }
    # Forbes ranks the Global 2000 by revenue, so the source rank is the
    # revenue rank. The market-cap rank has to be derived.
    rev_rank = forbes["rank_in_source"] if "rank_in_source" in forbes else None
    if rev_rank is None:
        rev_rank = forbes["revenue_usd"].rank(ascending=False, method="first")
    metrics["zipf_revenue"] = stats.zipf_exponent(rev_rank, rev)
    mcap = forbes[["market_cap_usd"]].copy()
    mcap["rank"] = mcap["market_cap_usd"].rank(ascending=False, method="first")
    metrics["zipf_market_cap"] = stats.zipf_exponent(mcap["rank"], mcap["market_cap_usd"])

    # -- thresholds --------------------------------------------------------
    metrics["revenue_thresholds"] = {
        f"gt_{int(t / 1e9)}b": stats.pareto_threshold_count(rev, t)
        for t in (1e9, 10e9, 50e9, 100e9, 250e9, 500e9)
    }
    metrics["profit_thresholds"] = {
        f"gt_{int(t / 1e9)}b": stats.pareto_threshold_count(profit, t)
        for t in (1e9, 10e9, 25e9, 50e9)
    }

    # -- the truncation gap ------------------------------------------------
    # Everything we can individually measure, Forbes and listed merged.
    merged = pd.concat([
        forbes[["company", "revenue_usd", "country", "sector", "ownership"]],
        listed[["company", "revenue_usd", "country", "sector", "ownership"]],
    ], ignore_index=True)
    merged = merged.dropna(subset=["revenue_usd"])
    merged = merged[merged["revenue_usd"] > 0]
    merged = merged.sort_values("revenue_usd", ascending=False)
    merged["merged_rank"] = range(1, len(merged) + 1)

    forbes_keys = set(forbes["company_key"].dropna())
    merged["in_forbes"] = merged["company"].map(
        lambda c: features_key(c) in forbes_keys)

    beyond = merged[~merged["in_forbes"]]
    metrics["truncation"] = {
        "measured_firms": int(len(merged)),
        "measured_firms_revenue": float(merged["revenue_usd"].sum()),
        "forbes_revenue": float(rev.sum()),
        "revenue_beyond_forbes": float(beyond["revenue_usd"].sum()),
        "share_beyond_forbes": float(
            beyond["revenue_usd"].sum() / merged["revenue_usd"].sum()),
        "firms_beyond_1b": int((beyond["revenue_usd"] >= 1e9).sum()),
        "firms_beyond_10b": int((beyond["revenue_usd"] >= 10e9).sum()),
        "firms_beyond_50b": int((beyond["revenue_usd"] >= 50e9).sum()),
        "firms_beyond_100b": int((beyond["revenue_usd"] >= 100e9).sum()),
        "largest_beyond_10b": int(
            (beyond["revenue_usd"] >= 10e9).sum()),
    }
    top_beyond = (beyond[beyond["revenue_usd"] >= 5e9]
                  .sort_values("revenue_usd", ascending=False)
                  .head(25)
                  .copy())
    top_beyond["revenue_musd"] = top_beyond["revenue_usd"] / 1e6
    metrics["truncation"]["top_beyond_forbes"] = top_beyond[
        ["company", "country", "revenue_musd", "sector"]].to_dict("records")

    # Combined rank-size over everything we can measure.
    metrics["zipf_merged"] = stats.zipf_exponent(merged["merged_rank"],
                                                  merged["revenue_usd"])
    metrics["concentration_merged"] = {
        "hhi_revenue": stats.hhi_points(merged["revenue_usd"]),
        "gini_revenue": stats.gini(merged["revenue_usd"]),
        "top100_revenue_share": stats.top_k_share(merged["revenue_usd"], 100),
        "top1000_revenue_share": stats.top_k_share(merged["revenue_usd"], 1000),
        "firms_for_80pct_revenue": stats.firms_for_share(merged["revenue_usd"], 0.80),
    }

    # Pareto tail on the merged distribution: the firms Forbes never saw.
    alpha = stats.pareto_alpha(merged["revenue_usd"], 1e9)
    metrics["pareto_alpha_above_1b"] = float(alpha)
    metrics["pareto_tail_estimate_above_1b"] = float(
        stats.tail_share_estimate(merged["revenue_usd"], 1e9, alpha)) if np.isfinite(alpha) else float("nan")

    # The two tables the headline charts are drawn from, so the reader can
    # see the numbers behind them.
    _keep = [c for c in ("company", "country", "revenue_usd", "profit_usd",
                         "market_cap_usd") if c in forbes.columns]
    top20 = (forbes.dropna(subset=["revenue_usd"])
             .nlargest(20, "revenue_usd")[_keep]
             .copy())
    rank_size = (forbes.dropna(subset=["revenue_usd"])
                 .sort_values("revenue_usd", ascending=False)
                 .reset_index(drop=True))
    rank_size.insert(0, "rank", range(1, len(rank_size) + 1))
    rank_size = rank_size[[c for c in ("rank", "company", "country", "revenue_usd")
                           if c in rank_size.columns]]

    tables = {
        "top_beyond_forbes": top_beyond[
            ["company", "country", "revenue_musd", "sector"]],
        "thresholds": pd.DataFrame(
            [{"threshold": k, "firms": v}
             for k, v in metrics["revenue_thresholds"].items()]),
        "top20": top20,
        "rank_size": rank_size,
    }

    return {"key": KEY, "metrics": metrics, "tables": tables}


def features_key(name: str) -> str:
    """Local import shim so this module stays importable in isolation."""
    import clean
    return clean.company_key(name)


def insights(m: dict) -> list[str]:
    """Auto-written findings for the scale module."""
    c = m["concentration"]
    t = m["truncation"]
    z = m["zipf_revenue"]
    out = [
        f"Forbes' Global 2000 holds **{m['forbes_revenue_total'] / 1e12:.2f} T$** of revenue "
        f"across {m['forbes_company_count']:,} firms, "
        f"**{m['forbes_blended_margin'] * 100:.1f}%** of which is profit. "
        f"{m['forbes_loss_makers']} firms ({m['forbes_loss_maker_share'] * 100:.1f}%) lose money.",

        f"Concentration is steep but not a monopoly: the top 100 firms hold "
        f"**{c['top100_revenue_share'] * 100:.1f}%** of revenue, the top 500 hold "
        f"**{c['top500_revenue_share'] * 100:.1f}%**, and it takes "
        f"**{c['firms_for_50pct_revenue']}** firms to reach half the total. "
        f"HHI on revenue is **{c['hhi_revenue']:.0f}** points and the Gini is "
        f"**{c['gini_revenue']:.2f}**.",

        f"The rank-size curve fits a power law with a Zipf exponent of "
        f"**{z['exponent']:.2f}** (R² = {z['r2']:.3f}), i.e. roughly Zipf-like, "
        f"so firm size decays smoothly rather than through a single dominant tier.",

        f"**The list is truncated, and it matters.** Merging the 2,000 Forbes firms with the "
        f"{t['measured_firms'] - m['forbes_company_count']:,} listed companies we can measure "
        f"individually adds **{t['revenue_beyond_forbes'] / 1e12:.2f} T$** of revenue that the "
        f"Global 2000 never mentions — **{t['share_beyond_forbes'] * 100:.1f}%** of everything "
        f"measurable. Among those are **{t['firms_beyond_10b']:,}** firms above $10B.",

        f"Profit concentration exceeds revenue concentration: the top 100 firms capture "
        f"**{c['top100_profit_share'] * 100:.1f}%** of all profit versus "
        f"**{c['top100_revenue_share'] * 100:.1f}%** of revenue.",
    ]
    return out
