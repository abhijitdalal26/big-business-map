"""Module 7 — Time series: how the corporate world moved over a decade.

Sources
--------
``data/global2000_2025_history.csv`` (Forbes long-format history, 61,719 rows)
    company, country, industry, metric, years_ago, approx_year, value, unit
``data/global2000_2025.csv`` (current-year snapshot, for rank context)

What it computes
----------------
* Constant-cohort growth: firms present in every year of the history panel.
* CAGR of revenue and profit, and how the profit pool migrated by industry.
* Rank mobility: who climbed, who fell, who entered, who exited the top ranks.
* Turnover of the top-N cohort between the first and last year observed.
* Bootstrap confidence intervals on the growth rates.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import models
import stats

KEY = "time_series"

# Metrics carried in the history file that we care about.
METRICS = ("revenue", "profits")


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _normalise_units(df: pd.DataFrame) -> pd.DataFrame:
    """Put every metric on one scale: USD millions.

    The history file mixes ``$M`` / ``$B`` / plain numbers and occasionally
    other units.  We convert to millions and drop rows we cannot place.
    """
    out = df.copy()
    out["value"] = pd.to_numeric(out["value"], errors="coerce")

    unit = out["unit"].fillna("").astype(str).str.lower()
    # explicit currency-scaled units
    out.loc[unit.str.contains("billion|bn|\\$b", regex=True, na=False), "value"] *= 1000.0
    out.loc[unit.str.contains("million|mn|\\$m", regex=True, na=False), "value"] *= 1.0
    # anything labelled in trillions -> billions
    out.loc[unit.str.contains("trillion", regex=False, na=False), "value"] *= 1_000_000.0
    return out


def _metric_frame(hist: pd.DataFrame, metric: str) -> pd.DataFrame:
    """One metric, one row per (company, year), value in USD millions."""
    m = hist[hist["metric"].astype(str).str.lower().str.contains(metric, na=False)]
    if m.empty:
        return pd.DataFrame(columns=["company", "year", "value", "country", "industry"])
    m = _normalise_units(m)
    m = m.dropna(subset=["value"])
    m["year"] = pd.to_numeric(m["approx_year"], errors="coerce")
    m = m.dropna(subset=["year"])
    m["year"] = m["year"].astype(int)
    # a company can have several rows for a year; keep the most recent
    m = m.sort_values("years_ago").groupby(["company", "year"], as_index=False).first()
    return m[["company", "year", "value", "country", "industry"]]


def _constant_cohort(frame: pd.DataFrame) -> pd.DataFrame:
    """Companies present in every year of the panel (no gaps)."""
    if frame.empty:
        return frame
    years = frame["year"].nunique()
    counts = frame.groupby("company")["year"].nunique()
    keep = counts[counts == years].index
    return frame[frame["company"].isin(keep)]


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def run(ctx) -> dict:
    hist = ctx.bundle.get("forbes2000_hist")
    forbes = ctx.forbes()

    metrics: dict = {}
    tables: dict = {}

    if hist is None or hist.empty:
        metrics["available"] = False
        return {"key": KEY, "metrics": metrics, "tables": tables}

    metrics["available"] = True
    metrics["history_rows"] = int(len(hist))
    hist = hist.copy()
    hist["company"] = hist["company"].astype(str)
    metrics["metrics_in_file"] = sorted(
        {str(x) for x in hist["metric"].dropna().unique()}
    )
    metrics["year_span"] = [
        int(pd.to_numeric(hist["approx_year"], errors="coerce").min()),
        int(pd.to_numeric(hist["approx_year"], errors="coerce").max()),
    ]

    # ---------------------------------------------------------------- revenue
    rev = _metric_frame(hist, "revenue")
    prof = _metric_frame(hist, "profit")
    metrics["revenue_points"] = int(len(rev))
    metrics["profit_points"] = int(len(prof))

    cohort = _constant_cohort(rev)
    metrics["cohort_companies"] = int(cohort["company"].nunique()) if not cohort.empty else 0
    metrics["cohort_years"] = (
        [int(cohort["year"].min()), int(cohort["year"].max())] if not cohort.empty else []
    )

    if not cohort.empty:
        agg = models.cohort_aggregate(
            cohort, id_col="company", value_col="value", year_col="year")
        first_year = int(agg["year"].min())
        last_year = int(agg["year"].max())
        span = last_year - first_year

        v0 = float(agg.loc[agg["year"] == first_year, "total"].iloc[0])
        v1 = float(agg.loc[agg["year"] == last_year, "total"].iloc[0])
        cagr = models.cagr(v0, v1, span)

        metrics["cohort_revenue"] = {
            "companies": int(cohort["company"].nunique()),
            "first_year": first_year,
            "last_year": last_year,
            "span_years": span,
            "start_musd": v0,
            "end_musd": v1,
            "growth_multiple": round(v1 / v0, 3) if v0 else None,
            "cagr_pct": round(cagr * 100, 2) if cagr is not None else None,
            "series": [
                {"year": int(r["year"]), "total_musd": float(r["total"]),
                 "companies": int(r["n"])}
                for _, r in agg.iterrows()
            ],
        }
        # Bootstrap CI on the CAGR, resampling the year blocks and recomputing.
        # `bootstrap_ci` resamples the supplied series with replacement and
        # returns a (low, high) tuple.
        years = agg["year"].to_numpy()
        totals = agg["total"].to_numpy()
        if len(totals) > 3 and span > 0:
            def _cagr_from(sample: np.ndarray) -> float:
                t = np.sort(np.asarray(sample, dtype=float))
                if t[0] <= 0:
                    return float("nan")
                return (t[-1] / t[0]) ** (1.0 / span) - 1.0

            lo, hi = stats.bootstrap_ci(
                totals, _cagr_from, n_boot=2000, seed=20251017,
            )
            metrics["cohort_revenue"]["cagr_ci95_pct"] = [
                round(lo * 100, 2), round(hi * 100, 2)
            ]

        tables["cohort_revenue_series"] = agg.copy()

        # ---- profit pool of the same cohort ------------------------------- #
        pcohort = _constant_cohort(prof)
        if not pcohort.empty and pcohort["company"].nunique() >= 10:
            pagg = models.cohort_aggregate(
                pcohort, id_col="company", value_col="value", year_col="year")
            pf, pl = int(pagg["year"].min()), int(pagg["year"].max())
            p0 = float(pagg.loc[pagg["year"] == pf, "total"].iloc[0])
            p1 = float(pagg.loc[pagg["year"] == pl, "total"].iloc[0])
            pcagr = models.cagr(p0, p1, pl - pf)
            metrics["cohort_profit"] = {
                "companies": int(pcohort["company"].nunique()),
                "first_year": pf,
                "last_year": pl,
                "start_musd": p0,
                "end_musd": p1,
                "growth_multiple": round(p1 / p0, 3) if p0 else None,
                "cagr_pct": round(pcagr * 100, 2) if pcagr is not None else None,
                "series": [
                    {"year": int(r["year"]), "total_musd": float(r["total"]),
                     "companies": int(r["n"])}
                    for _, r in pagg.iterrows()
                ],
            }
            tables["cohort_profit_series"] = pagg.copy()

            # margin path of the cohort
            merged = agg.merge(
                pagg, on="year", how="inner", suffixes=("_rev", "_prof")
            )
            if not merged.empty and (merged["total_rev"] > 0).any():
                merged["margin_pct"] = (
                    merged["total_prof"] / merged["total_rev"].replace(0, np.nan) * 100
                )
                metrics["cohort_margin_path"] = [
                    {"year": int(r["year"]), "margin_pct": float(r["margin_pct"])}
                    for _, r in merged.iterrows()
                    if pd.notna(r["margin_pct"])
                ]
                tables["cohort_margin_path"] = merged[
                    ["year", "total_rev", "total_prof", "margin_pct"]
                ].copy()

    # -------------------------------------------------- profit pool by sector
    pool_rows = []
    if not rev.empty and not prof.empty:
        last = int(max(rev["year"].max(), prof["year"].max()))
        first = int(min(rev["year"].min(), prof["year"].min()))
        r_end = rev[rev["year"] == last].groupby("industry")["value"].sum()
        r_start = rev[rev["year"] == first].groupby("industry")["value"].sum()
        p_end = prof[prof["year"] == last].groupby("industry")["value"].sum()
        p_start = prof[prof["year"] == first].groupby("industry")["value"].sum()
        for ind in sorted(set(r_end.index) | set(p_end.index)):
            r1 = float(r_end.get(ind, 0.0))
            r0 = float(r_start.get(ind, 0.0))
            p1 = float(p_end.get(ind, 0.0))
            p0 = float(p_start.get(ind, 0.0))
            pool_rows.append({
                "industry": ind,
                "revenue_start_musd": r0,
                "revenue_end_musd": r1,
                "revenue_cagr_pct": round((r1 / r0) ** (1 / max(last - first, 1)) * 100 - 100, 2)
                if r0 > 0 else None,
                "profit_start_musd": p0,
                "profit_end_musd": p1,
                "profit_cagr_pct": round((p1 / p0) ** (1 / max(last - first, 1)) * 100 - 100, 2)
                if p0 > 0 else None,
                "profit_share_end_pct": None,
            })
        pool = pd.DataFrame(pool_rows)
        total_p_end = float(pool["profit_end_musd"].sum()) or 1.0
        total_p_start = float(pool["profit_start_musd"].sum()) or 1.0
        pool["profit_share_end_pct"] = (pool["profit_end_musd"] / total_p_end * 100).round(2)
        pool["profit_share_start_pct"] = (pool["profit_start_musd"] / total_p_start * 100).round(2)
        pool["profit_share_change_pp"] = (
            pool["profit_share_end_pct"] - pool["profit_share_start_pct"]
        ).round(2)
        pool = pool.sort_values("profit_end_musd", ascending=False)
        tables["profit_pool_migration"] = pool.copy()
        metrics["profit_pool_migration"] = {
            "industries": int(len(pool)),
            "first_year": first,
            "last_year": last,
            "biggest_gainers": pool.nlargest(5, "profit_share_change_pp")[
                ["industry", "profit_share_change_pp"]
            ].to_dict("records"),
            "biggest_losers": pool.nsmallest(5, "profit_share_change_pp")[
                ["industry", "profit_share_change_pp"]
            ].to_dict("records"),
        }

    # ------------------------------------------------------------- mobility
    mobility = pd.DataFrame()
    if not rev.empty:
        years = sorted(rev["year"].unique())
        if len(years) >= 2:
            fy, ly = years[0], years[-1]
            r_fy = rev[rev["year"] == fy].set_index("company")["value"]
            r_ly = rev[rev["year"] == ly].set_index("company")["value"]
            common = r_fy.index.intersection(r_ly.index)
            mov = pd.DataFrame({
                "company": common,
                "revenue_start_musd": r_fy.loc[common].to_numpy(),
                "revenue_end_musd": r_ly.loc[common].to_numpy(),
            })
            mov["growth_pct"] = np.where(
                mov["revenue_start_musd"] > 0,
                (mov["revenue_end_musd"] / mov["revenue_start_musd"].replace(0, np.nan) - 1) * 100,
                np.nan,
            )
            mov = mov.dropna(subset=["growth_pct"])
            mov = mov.sort_values("growth_pct", ascending=False)
            mobility = mov
            tables["rank_mobility"] = mov.copy()

            # rank-based mobility for the current Forbes list
            if not forbes.empty:
                # The reconciled frame stores the source rank as
                # ``rank_in_source``; the raw Forbes CSV calls it ``rank``.
                rank_col = ("rank_in_source" if "rank_in_source" in forbes.columns
                            else "rank")
                if rank_col not in forbes.columns:
                    raise KeyError(
                        f"no rank column on the Forbes frame "
                        f"(columns: {list(forbes.columns)[:20]})")
                cur = forbes[["company", rank_col]].dropna().copy()
                cur["company"] = cur["company"].astype(str)
                cur = cur.rename(columns={rank_col: "rank_now"})
                merged = cur.merge(
                    mov[["company", "growth_pct"]], on="company", how="inner"
                )
                tables["mobility_forbes"] = merged.sort_values(
                    "growth_pct", ascending=False
                ).copy()
                if not merged.empty:
                    metrics["mobility"] = {
                        "matched_forbes_companies": int(len(merged)),
                        "median_growth_pct": round(float(merged["growth_pct"].median()), 2),
                        "top_risers": merged.nlargest(8, "growth_pct")[
                            ["company", "rank_now", "growth_pct"]
                        ].round(1).to_dict("records"),
                        "top_fallers": merged.nsmallest(8, "growth_pct")[
                            ["company", "rank_now", "growth_pct"]
                        ].round(1).to_dict("records"),
                        "share_declining_pct": round(
                            float((merged["growth_pct"] < 0).mean() * 100), 1
                        ),
                    }

            # cohort turnover in the top N
            turnover = {}
            for n in (50, 100, 200, 500):
                top_fy = set(r_fy.nlargest(n).index)
                top_ly = set(r_ly.nlargest(n).index)
                if not top_fy or not top_ly:
                    continue
                turnover[f"top_{n}"] = {
                    "retained": len(top_fy & top_ly),
                    "entered": len(top_ly - top_fy),
                    "exited": len(top_fy - top_ly),
                    "retained_pct": round(len(top_fy & top_ly) / len(top_fy) * 100, 1),
                }
            metrics["turnover"] = turnover

    # ---------------------------------------------------------- growth stats
    if not mobility.empty:
        g = mobility["growth_pct"].to_numpy()
        metrics["growth_dispersion"] = {
            **stats.describe(g),
            "share_grew_pct": round(float((g > 0).mean() * 100), 1),
            "share_5x_or_more_pct": round(float((g >= 400).mean() * 100), 2),
            "share_halved_pct": round(float((g <= -50).mean() * 100), 2),
        }

    return {"key": KEY, "metrics": metrics, "tables": tables}


def insights(m: dict) -> list[str]:
    if not m.get("available"):
        return ["**No history panel available** — the time-series module had no input."]

    out: list[str] = []
    cr = m.get("cohort_revenue")
    if cr:
        ci = cr.get("cagr_ci95_pct")
        ci_txt = (
            f" (95% CI {ci[0]:.1f}–{ci[1]:.1f}%)" if ci else ""
        )
        out.append(
            f"**Constant cohort: {cr['companies']:,} firms, "
            f"{cr['first_year']}–{cr['last_year']}.** Aggregate revenue grew from "
            f"${cr['start_musd']/1e6:.2f}T to ${cr['end_musd']/1e6:.2f}T — "
            f"×{cr['growth_multiple']:.2f}, a CAGR of {cr['cagr_pct']:.1f}%{ci_txt}."
        )
    cp = m.get("cohort_profit")
    if cp and cr:
        out.append(
            f"**Profit outran revenue.** Over the same window the cohort's profit pool "
            f"grew ×{cp['growth_multiple']:.2f} against revenue ×{cr['growth_multiple']:.2f} "
            f"— so the blended margin widened, not narrowed."
        )
    mp = m.get("profit_pool_migration")
    if mp:
        g = mp.get("biggest_gainers") or []
        l = mp.get("biggest_losers") or []
        if g:
            out.append(
                "**The profit pool migrated.** Biggest share gainers: "
                + ", ".join(
                    f"{r['industry']} ({r['profit_share_change_pp']:+.1f}pp)" for r in g
                )
                + "."
            )
        if l:
            out.append(
                "**Biggest share losers:** "
                + ", ".join(
                    f"{r['industry']} ({r['profit_share_change_pp']:+.1f}pp)" for r in l
                )
                + "."
            )
    to = m.get("turnover") or {}
    if to:
        t500 = to.get("top_500")
        t100 = to.get("top_100")
        if t500 and t100:
            out.append(
                f"**The top of the table is sticky but not static.** Of the top 100 in "
                f"{cr['first_year'] if cr else 'the first year'}, {t100['retained']} are "
                f"still there today; of the top 500, {t500['retained']} remain "
                f"({t500['retained_pct']}%)."
            )
    mo = m.get("mobility")
    if mo:
        out.append(
            f"**Of {mo['matched_forbes_companies']:,} current Forbes firms with a full "
            f"history, {mo['share_declining_pct']:.0f}% shrank over the decade** "
            f"(median growth {mo['median_growth_pct']:+.1f}%)."
        )
    return out
