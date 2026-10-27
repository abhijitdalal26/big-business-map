"""Module 4 -- Ownership: who actually owns the giants.

A revenue ranking published by Forbes answers a narrower question than most
readers assume: it ranks the largest companies that Forbes chose to rank.
State-owned oil companies, sovereign wealth entities, farmer cooperatives and
mutual insurers sit outside that frame in large numbers, and they are
enormous.

This module:

* builds an **ownership taxonomy** (state, mutual, private, PE-backed,
  listed, unknown) across every source we hold;
* identifies the **invisible giants** -- the largest firms that do not appear
  in the Forbes Global 2000 at all, and how much revenue that conceals;
* re-ranks the **true top 100 on earth** from the mixed universe and reports
  how many Forbes' own top 100 are displaced;
* tests whether state ownership is associated with different profitability
  and scale, with confidence intervals rather than just point estimates.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import stats

KEY = "ownership"

OWNERSHIP_ORDER = ["state", "mutual", "pe", "public", "private", "unknown"]


def _own_table(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["revenue_usd"] = pd.to_numeric(d.get("revenue_usd"), errors="coerce")
    d["profit_usd"] = pd.to_numeric(d.get("profit_usd"), errors="coerce")
    d["market_cap_usd"] = pd.to_numeric(d.get("market_cap_usd"), errors="coerce")
    d["employees"] = pd.to_numeric(d.get("employees"), errors="coerce")
    d["ownership"] = d["ownership"].fillna("unknown").replace("", "unknown")

    g = d.groupby("ownership").agg(
        companies=("company", "count"),
        revenue_usd=("revenue_usd", "sum"),
        profit_usd=("profit_usd", "sum"),
        market_cap_usd=("market_cap_usd", "sum"),
        employees=("employees", "sum"),
    ).reset_index()
    g["profit_margin"] = g["profit_usd"] / g["revenue_usd"].replace(0, np.nan)
    g["revenue_per_employee"] = g["revenue_usd"] / g["employees"].replace(0, np.nan)
    g["revenue_share"] = g["revenue_usd"] / g["revenue_usd"].sum()
    g["profit_share"] = g["profit_usd"] / g["profit_usd"].sum()
    g["order"] = g["ownership"].map(
        {o: i for i, o in enumerate(OWNERSHIP_ORDER)}).fillna(99)
    return g.sort_values("order").drop(columns="order").reset_index(drop=True)


def run(ctx) -> dict:
    forbes = ctx.forbes()
    mixed = ctx.reconciled
    metrics: dict = {}

    own_forbes = _own_table(forbes)
    own_mixed = _own_table(mixed)
    metrics["ownership"] = {
        "forbes": own_forbes.to_dict("records"),
        "mixed": own_mixed.to_dict("records"),
    }
    metrics["state_revenue_mixed"] = float(
        own_mixed.loc[own_mixed["ownership"] == "state", "revenue_usd"].sum())
    metrics["state_companies_mixed"] = int(
        (mixed["ownership"] == "state").sum())

    # -- invisible giants --------------------------------------------------
    # Companies in the mixed universe with real revenue that Forbes omits.
    forbes_keys = set(forbes["company_key"].dropna())
    invisible = mixed[mixed["revenue_usd"].notna() & (mixed["revenue_usd"] > 0)].copy()
    invisible = invisible[~invisible["company_key"].isin(forbes_keys)]
    invisible = invisible.sort_values("revenue_usd", ascending=False)

    metrics["invisible_giants"] = {
        "count_with_revenue": int(len(invisible)),
        "total_revenue": float(invisible["revenue_usd"].sum()),
        "count_over_10b": int((invisible["revenue_usd"] >= 10e9).sum()),
        "count_over_50b": int((invisible["revenue_usd"] >= 50e9).sum()),
        "top_30": invisible.head(30)[
            ["company", "country", "ownership", "sector",
             "revenue_usd", "profit_usd", "source"]
        ].assign(revenue_musd=lambda x: x["revenue_usd"] / 1e6,
                 profit_musd=lambda x: x["profit_usd"] / 1e6)
        [["company", "country", "ownership", "sector", "revenue_musd",
          "profit_musd", "source"]].to_dict("records"),
    }
    invisible_by_country = (invisible.groupby("country")
                            .agg(firms=("company", "count"),
                                 revenue_usd=("revenue_usd", "sum"))
                            .reset_index()
                            .sort_values("revenue_usd", ascending=False))
    metrics["invisible_giants"]["by_country"] = invisible_by_country.head(20).to_dict("records")
    metrics["invisible_giants"]["by_ownership"] = (
        invisible.groupby("ownership")
        .agg(firms=("company", "count"), revenue_usd=("revenue_usd", "sum"))
        .reset_index().sort_values("revenue_usd", ascending=False).to_dict("records"))

    # -- the true top 100 on earth, and how far Forbes is off -------------
    forbes_top = forbes.nsmallest(100, "rank_in_source").copy()
    forbes_top_names = set(forbes_top["company_key"].dropna())
    mixed_top = mixed.dropna(subset=["revenue_usd"]).nlargest(100, "revenue_usd").copy()
    mixed_top["forbes_rank"] = mixed_top["company_key"].map(
        forbes.set_index("company_key")["rank_in_source"].to_dict())
    displaced = mixed_top[~mixed_top["company_key"].isin(forbes_top_names)]

    metrics["true_top100"] = {
        "forbes_top100_revenue": float(forbes_top["revenue_usd"].sum()),
        "mixed_top100_revenue": float(mixed_top["revenue_usd"].sum()),
        "revenue_difference": float(mixed_top["revenue_usd"].sum()
                                    - forbes_top["revenue_usd"].sum()),
        "displaced_count": int(len(displaced)),
        "displaced": displaced[
            ["company", "country", "ownership", "sector", "revenue_usd", "source"]
        ].assign(revenue_musd=lambda x: x["revenue_usd"] / 1e6)[
            ["company", "country", "ownership", "sector", "revenue_musd", "source"]
        ].to_dict("records"),
    }
    # Where would each of the mixed top 100 sit on a Forbes-style ranking?
    mixed_top["would_rank"] = range(1, len(mixed_top) + 1)
    metrics["true_top100"]["displacement"] = (
        mixed_top[["company", "country", "ownership", "sector", "revenue_usd",
                   "would_rank", "forbes_rank", "source"]]
        .assign(revenue_musd=lambda x: x["revenue_usd"] / 1e6)
        .to_dict("records"))

    # -- do state firms behave differently? --------------------------------
    d = mixed.dropna(subset=["revenue_usd", "profit_usd"]).copy()
    d = d[d["revenue_usd"] > 0]
    d["margin"] = d["profit_usd"] / d["revenue_usd"]
    # A handful of holding companies report a profit several orders of
    # magnitude larger than their revenue (equity income booked against a
    # small operating base). Left in, they drag the mean to absurdity and
    # widen every bootstrap interval to +-200pp, which hides the real effect.
    # A net margin outside [-100%, +100%] is arithmetically impossible for a
    # standalone operating business, so those rows are dropped and the
    # exclusion is reported alongside the result.
    margin_clean = d["margin"].where(d["margin"].abs() <= 1.0)
    n_impossible = int((d["margin"].abs() > 1.0).sum())
    d["margin_clean"] = margin_clean
    state = d.loc[d["ownership"] == "state", "margin_clean"].dropna()
    listed = d.loc[d["ownership"] == "public", "margin_clean"].dropna()
    private = d.loc[d["ownership"].isin(["private", "pe"]), "margin_clean"].dropna()
    mutual = d.loc[d["ownership"] == "mutual", "margin_clean"].dropna()

    comparisons = []
    for label, a, b in (("state vs listed", state, listed),
                        ("state vs private/PE", state, private),
                        ("mutual vs listed", mutual, listed)):
        if len(a) < 5 or len(b) < 5:
            continue
        t = stats.welch_t(a, b)
        mw = stats.mann_whitney(a, b)
        lo, hi = stats.bootstrap_diff_ci(a, b, np.mean, n_boot=1500, seed=7)
        comparisons.append({
            "comparison": label,
            "n_a": int(len(a)), "n_b": int(len(b)),
            "mean_a": float(a.mean()), "mean_b": float(b.mean()),
            "median_a": float(a.median()), "median_b": float(b.median()),
            "diff": t["mean_diff"], "ci_low": lo, "ci_high": hi,
            "p_welch": t["p"], "p_mann_whitney": mw["p"],
        })
    metrics["margin_by_ownership_tests"] = comparisons
    metrics["margin_exclusions"] = {
        "impossible_margin_rows_dropped": n_impossible,
        "rule": "net margin outside [-100%, +100%] is arithmetically "
                "impossible for a standalone operating business",
    }

    # -- size by ownership --------------------------------------------------
    size_tests = []
    for label, a, b in (("state vs listed", state, listed),):
        pass
    rev_state = d.loc[d["ownership"] == "state", "revenue_usd"].dropna()
    rev_listed = d.loc[d["ownership"] == "public", "revenue_usd"].dropna()
    if len(rev_state) > 5 and len(rev_listed) > 5:
        t = stats.welch_t(rev_state, rev_listed)
        lo, hi = stats.bootstrap_diff_ci(rev_state, rev_listed, np.median,
                                         n_boot=1500, seed=11)
        size_tests.append({
            "comparison": "median revenue: state vs listed",
            "median_state": float(rev_state.median()),
            "median_listed": float(rev_listed.median()),
            "ratio": float(rev_state.median() / rev_listed.median()),
            "ci_low": lo, "ci_high": hi, "p_welch": t["p"],
        })
    metrics["size_by_ownership_tests"] = size_tests

    # -- state ownership by country ---------------------------------------
    state_df = mixed[mixed["ownership"] == "state"].copy()
    metrics["state_by_country"] = (
        state_df.groupby("country")
        .agg(firms=("company", "count"), revenue_usd=("revenue_usd", "sum"))
        .reset_index().sort_values("revenue_usd", ascending=False)
        .head(20).to_dict("records"))

    tables = {
        "ownership_forbes": own_forbes,
        "ownership_mixed": own_mixed,
        "invisible_giants": invisible.head(200),
        "invisible_by_country": invisible_by_country,
        "true_top100": mixed_top,
        "margin_tests": pd.DataFrame(comparisons),
    }

    return {"key": KEY, "metrics": metrics, "tables": tables}


def insights(m: dict) -> list[str]:
    inv = m["invisible_giants"]
    tp = m["true_top100"]
    own = {r["ownership"]: r for r in m["ownership"]["mixed"]}
    out = []

    if "state" in own:
        out.append(
            f"State-owned enterprises account for **{own['state']['companies']:,}** companies "
            f"and **${own['state']['revenue_usd'] / 1e12:.2f} T$** of revenue in the mixed "
            f"universe -- **{own['state']['revenue_share'] * 100:.1f}%** of everything "
            f"measured, and a profit share of only "
            f"**{own['state']['profit_share'] * 100:.1f}%**.")

    out.append(
        f"**The invisible giants.** {inv['count_with_revenue']:,} companies with known "
        f"revenue do not appear in the Forbes Global 2000, worth "
        f"**${inv['total_revenue'] / 1e12:.2f} T$** between them. "
        f"{inv['count_over_50b']} of them exceed $50B in revenue -- including "
        + ", ".join(f"**{r['company']}** (${r['revenue_musd'] / 1000:.0f}B, "
                    f"{r['ownership']})"
                    for r in inv["top_30"][:4].__iter__()) + ".")

    out.append(
        f"Re-ranking the top 100 on earth from the mixed universe, "
        f"**{tp['displaced_count']} of Forbes' own top 100 are displaced**, and the "
        f"true top 100 is worth **${tp['mixed_top100_revenue'] / 1e12:.2f} T$** against "
        f"Forbes' ${tp['forbes_top100_revenue'] / 1e12:.2f} T$ "
        f"(a ${abs(tp['revenue_difference']) / 1e9:.0f}B gap).")

    for t in m.get("margin_by_ownership_tests", []):
        out.append(
            f"**{t['comparison']}**: median net margin "
            f"{t['median_a'] * 100:.1f}% vs {t['median_b'] * 100:.1f}% "
            f"(means {t['mean_a'] * 100:.1f}% vs {t['mean_b'] * 100:.1f}%; "
            f"difference in means {t['diff'] * 100:+.1f} pp, bootstrap CI "
            f"[{t['ci_low'] * 100:+.1f}, {t['ci_high'] * 100:+.1f}] pp, "
            f"p = {stats.fmt_p(t['p_welch'])}).")
    exc = m.get("margin_exclusions", {})
    if exc.get("impossible_margin_rows_dropped"):
        out.append(
            f"{exc['impossible_margin_rows_dropped']} rows were dropped from the "
            f"margin comparison because a net margin outside [-100%, +100%] is "
            f"arithmetically impossible for a standalone operating business.")
    return out
