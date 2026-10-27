"""Module 8 — Data quality: how much of this can you actually trust?

This module is deliberately the last one.  Every number in the report rests on
a source with a different vintage, a different definition and a different
degree of completeness, and this module quantifies that.

What it computes
----------------
* A missingness matrix for every dataset and every column.
* Cross-source revenue disagreement: for companies that appear in more than
  one source, how far apart are the revenue numbers?  Broken down by source
  pair, because "Forbes vs SEC" and "Forbes vs Wikipedia" are very different
  comparisons.
* Self-validation of the Wikipedia top-up: the country-list pages carry
  Forbes' own rank for each company, so we can check our new rows against
  the source they were scraped from.
* Outlier / implausibility detection on the financial columns.
* A per-company confidence score that is carried into the report.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import clean
import stats

KEY = "data_quality"

# Trust ranking used for the confidence score.  Higher is better.
SOURCE_TRUST = {
    "sec_filing": 1.00,
    "forbes": 0.85,
    "fortune": 0.80,
    "wikipedia": 0.60,
    "estimate": 0.45,
    "unknown": 0.30,
}

# Datasets profiled in the missingness matrix.
PROFILE_ORDER = [
    "forbes2000",
    "fortune500",
    "fortune_profiles",
    "wiki_countries",
    "listed",
    "exchanges",
    "exchange_top",
    "unicorns",
    "private_us",
    "ai_companies",
    "ai_labs",
    "hf_stats",
    "forbes2000_hist",
    "profiles",
    "worldbank_extra",
]

# Financial columns checked for implausible values.
FIN_COLS = ["revenue_usd", "profit_usd", "assets_usd", "market_cap_usd"]


# --------------------------------------------------------------------------- #
# missingness
# --------------------------------------------------------------------------- #
def _missingness(bundle) -> tuple[pd.DataFrame, list[dict]]:
    rows: list[dict] = []
    for key in PROFILE_ORDER:
        df = bundle.get(key)
        if df is None or df.empty:
            continue
        n = len(df)
        for col in df.columns:
            nulls = int(df[col].isna().sum())
            blank = int(
                df[col].astype(str).str.strip().isin(["", "nan", "None", "NaN"]).sum()
            )
            miss = max(nulls, blank)
            rows.append({
                "dataset": key,
                "column": col,
                "rows": n,
                "missing": miss,
                "missing_pct": round(miss / n * 100, 1),
                "distinct": int(df[col].nunique(dropna=True)),
            })
    frame = pd.DataFrame(rows)
    summary = []
    if not frame.empty:
        for key, g in frame.groupby("dataset"):
            total = int(g["rows"].iloc[0])
            # fraction of cells that are missing across all columns
            cell_miss = g["missing"].sum() / (total * max(len(g), 1)) * 100
            summary.append({
                "dataset": key,
                "rows": total,
                "columns": int(len(g)),
                "cell_missing_pct": round(float(cell_miss), 1),
                "worst_column": g.nlargest(1, "missing_pct").iloc[0]["column"],
                "worst_column_missing_pct": float(
                    g["missing_pct"].max()
                ),
            })
    return frame, summary


# --------------------------------------------------------------------------- #
# cross-source disagreement
# --------------------------------------------------------------------------- #
def _source_matrix(uni: pd.DataFrame) -> pd.DataFrame:
    """One row per (company_key, source) with the revenue it claims."""
    if uni.empty:
        return pd.DataFrame()
    u = uni[uni["revenue_usd"].notna() & (uni["revenue_usd"] > 0)]
    if u.empty:
        return pd.DataFrame()
    u = u.groupby(["company_key", "source"], as_index=False).agg(
        revenue_usd=("revenue_usd", "median"),
        n_obs=("revenue_usd", "size"),
    )
    return u


def _disagreement(mat: pd.DataFrame, a: str, b: str) -> dict:
    """Compare revenue claimed by source *a* against source *b*."""
    if mat.empty:
        return {}
    pa = mat[mat["source"] == a].set_index("company_key")["revenue_usd"]
    pb = mat[mat["source"] == b].set_index("company_key")["revenue_usd"]
    common = pa.index.intersection(pb.index)
    if len(common) < 5:
        return {"pairs": int(len(common)), "note": "too few matches"}
    x = pa.loc[common].to_numpy()
    y = pb.loc[common].to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        mid = (x + y) / 2.0
        pdiff = np.where(mid != 0, np.abs(x - y) / np.abs(mid) * 100.0, np.nan)
    return {
        "pairs": int(len(common)),
        "median_abs_pct_diff": round(stats.median_absolute_pct_diff(x, y), 1),
        "mean_abs_pct_diff": round(float(np.nanmean(np.abs(pdiff))), 1),
        "p90_abs_pct_diff": round(float(np.nanpercentile(np.abs(pdiff), 90)), 1),
        "share_within_10pct": round(float((np.abs(pdiff) <= 10).mean() * 100), 1),
        "share_within_25pct": round(float((np.abs(pdiff) <= 25).mean() * 100), 1),
        "share_over_2x": round(float((np.maximum(x, y) / np.minimum(x, y) > 2).mean() * 100), 1),
        "pearson_r": round(float(np.corrcoef(x, y)[0, 1]), 3) if len(common) > 3 else None,
    }


def _disagreement_table(mat: pd.DataFrame, sources: list[str]) -> pd.DataFrame:
    rows = []
    for i, a in enumerate(sources):
        for b in sources[i + 1:]:
            d = _disagreement(mat, a, b)
            if d.get("pairs"):
                rows.append({"source_a": a, "source_b": b, **d})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# outliers
# --------------------------------------------------------------------------- #
def _outliers(reconciled: pd.DataFrame) -> dict:
    if reconciled.empty:
        return {}
    out: dict = {}
    for col in FIN_COLS:
        if col not in reconciled.columns:
            continue
        v = pd.to_numeric(reconciled[col], errors="coerce")
        v = v[v > 0]
        if v.empty:
            continue
        # `v` keeps the frame's index; z-scoring the numpy array instead would
        # rebuild a RangeIndex and silently misalign against `flag`.
        z = stats.zscore(v)
        flag = reconciled.loc[v.index]
        extreme = flag.assign(_z=z).loc[z > 6]
        out[col] = {
            "n": int(len(v)),
            "median": float(v.median()),
            "p99": float(v.quantile(0.99)),
            "max": float(v.max()),
            "extreme_count": int(len(extreme)),
            "extreme_share_pct": round(len(extreme) / len(v) * 100, 3),
            "extreme_examples": extreme.nlargest(3, col)[
                ["company", col, "country"]
            ].to_dict("records") if len(extreme) else [],
        }
    return out


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def run(ctx) -> dict:
    bundle = ctx.bundle
    uni = ctx.universe
    rec = ctx.reconciled

    metrics: dict = {}
    tables: dict = {}

    # ------------------------------------------------------- missingness
    miss, summary = _missingness(bundle)
    metrics["missingness_summary"] = summary
    if not miss.empty:
        tables["missingness"] = miss.copy()
        # only the columns that actually matter, ranked
        key_cols = [
            "revenue_usd", "profit_usd", "assets_usd", "market_cap_usd",
            "employees", "country", "sector", "ownership", "industry",
        ]
        sub = miss[miss["column"].isin(key_cols)]
        if not sub.empty:
            tables["missingness_key"] = sub.sort_values(
                "missing_pct", ascending=False
            ).copy()

    # --------------------------------------------- cross-source agreement
    mat = _source_matrix(uni)
    sources = sorted(set(mat["source"])) if not mat.empty else []
    metrics["sources_compared"] = sources
    if not mat.empty:
        metrics["companies_in_multiple_sources"] = int(
            (mat.groupby("company_key")["source"].nunique() > 1).sum()
        )
        metrics["total_matched_companies"] = int(mat["company_key"].nunique())
        dis = _disagreement_table(mat, sources)
        if not dis.empty:
            tables["cross_source_disagreement"] = dis.copy()
            metrics["cross_source_disagreement"] = dis.to_dict("records")

            # a headline: Forbes vs the SEC filings, and Forbes vs Wikipedia
            for a, b in (("forbes", "listed"), ("forbes", "fortune"),
                         ("forbes", "wiki"), ("listed", "fortune")):
                d = _disagreement(mat, a, b)
                if d.get("pairs"):
                    metrics[f"agreement_{a}_vs_{b}"] = d

    # ------------------------------------- self-validation of the wiki top-up
    wiki = bundle.get("wiki_countries")
    if wiki is not None and not wiki.empty and "forbes2000_rank" in wiki.columns:
        has_rank = wiki[pd.to_numeric(wiki["forbes2000_rank"], errors="coerce").notna()]
        metrics["wiki_pages_with_forbes_crossref"] = int(
            wiki["list_page"].nunique() if "list_page" in wiki.columns else 0
        )
        metrics["wiki_rows_carrying_forbes_rank"] = int(len(has_rank))
        if not has_rank.empty:
            fr = pd.to_numeric(has_rank["forbes2000_rank"], errors="coerce")
            metrics["wiki_forbes_rank_range"] = [
                int(fr.min()), int(fr.max())
            ]

    # compare wiki revenue with Forbes revenue for the same company
    if not mat.empty and {"wiki", "forbes"} <= set(mat["source"]):
        d = _disagreement(mat, "wiki", "forbes")
        if d.get("pairs"):
            metrics["wiki_vs_forbes_revenue"] = d

    # ------------------------------------------- Forbes vs Wikipedia coverage
    forbes = ctx.forbes()
    if wiki is not None and not wiki.empty and not forbes.empty:
        wkeys = {clean.company_key(str(c)) for c in wiki["company"].dropna()}
        fkeys = {clean.company_key(str(c)) for c in forbes["company"].dropna()}
        overlap = wkeys & fkeys
        metrics["wiki_forbes_overlap"] = {
            "wiki_companies": len(wkeys),
            "forbes_companies": len(fkeys),
            "overlap": len(overlap),
            "wiki_share_also_in_forbes_pct": round(
                len(overlap) / len(wkeys) * 100, 1
            ) if wkeys else None,
            "wiki_only": len(wkeys - fkeys),
        }

    # ---------------------------------------------------------- outliers
    metrics["outliers"] = _outliers(rec)

    # ------------------------------------------- per-company confidence score
    if not rec.empty and "revenue_basis" in rec.columns:
        trust = rec["revenue_basis"].map(SOURCE_TRUST).fillna(0.30)
        conf = trust.copy()

        # corroboration: how many independent sources also list this company?
        if "n_sources" in rec.columns:
            conf = conf + (rec["n_sources"].clip(upper=3) - 1) * 0.10
        # completeness: do we have profit and employees too?
        for col, bonus in (("profit_usd", 0.05), ("employees", 0.05)):
            if col in rec.columns:
                conf = conf + rec[col].notna().astype(float) * bonus
        # penalise extreme values
        if "market_cap_to_revenue" in rec.columns:
            mv = rec["market_cap_to_revenue"]
            conf = conf - ((mv > 60) | (mv < 0.05)).astype(float) * 0.05

        conf = conf.clip(0.0, 1.0)
        rec2 = rec.copy()
        rec2["confidence_score"] = conf.round(3)
        tables["confidence"] = (
            rec2[["company", "revenue_basis", "n_sources", "confidence_score"]]
            .sort_values("confidence_score")
            .head(200)
            .copy()
        )
        metrics["confidence"] = {
            "mean": round(float(conf.mean()), 3),
            "median": round(float(conf.median()), 3),
            "p10": round(float(conf.quantile(0.10)), 3),
            "p90": round(float(conf.quantile(0.90)), 3),
            "by_basis": rec2.groupby("revenue_basis")["confidence_score"]
            .agg(["count", "mean"])
            .round(3)
            .reset_index()
            .to_dict("records"),
        }

    # ------------------------------------------- vintage spread (the quiet trap)
    vintages = []
    for label, df, col in (
        ("Forbes Global 2000", forbes, "revenue_year"),
        ("Listed universe (SEC)", ctx.listed(), "revenue_year"),
    ):
        if df is not None and not df.empty and col in df.columns:
            v = pd.to_numeric(df[col], errors="coerce").dropna()
            if not v.empty:
                vintages.append({
                    "dataset": label,
                    "min_year": int(v.min()),
                    "max_year": int(v.max()),
                    "mode_year": int(v.mode().iloc[0]) if not v.mode().empty else None,
                })
    fp = bundle.get("fortune_profiles")
    if fp is not None and not fp.empty and "market_value_asof" in fp.columns:
        yrs = pd.to_datetime(fp["market_value_asof"], errors="coerce").dt.year.dropna()
        if not yrs.empty:
            vintages.append({
                "dataset": "Fortune profiles (market value)",
                "min_year": int(yrs.min()),
                "max_year": int(yrs.max()),
                "mode_year": int(yrs.mode().iloc[0]) if not yrs.mode().empty else None,
            })
    metrics["data_vintages"] = vintages
    tables["data_vintages"] = pd.DataFrame(vintages)

    # --------------------------------------------------- known caveats ledger
    metrics["caveats"] = [
        {
            "topic": "Revenue is a flow, not value added",
            "detail": "Company revenue double-counts intermediate goods across the "
                      "supply chain. Global 2000 revenue equals ~47% of world GDP "
                      "only as a scale statement.",
        },
        {
            "topic": "Fortune's company_type mislabels state firms",
            "detail": "Fortune reports several Chinese state enterprises as 'Private'. "
                      "Ownership for 104 names was hand-labelled in "
                      "data/fortune_labels.csv and applied here.",
        },
        {
            "topic": "Exchange market caps are not world market cap",
            "detail": "The 60 exchanges cover ~148T USD, but listed domestic companies "
                      "number ~48,000 worldwide, so this is a coverage figure, not a total.",
        },
        {
            "topic": "Unicorn valuations are marks, not prices",
            "detail": "Private valuations are the price of the most recent round, "
                      "usually preferred stock with a preference. They are not "
                      "realisable and not comparable to market capitalisation.",
        },
        {
            "topic": "The listed universe is US-complete and world-partial",
            "detail": "5,500 US names carry SEC XBRL revenue; the rest carry a "
                      "market-cap-site estimate. Country counts measure coverage, "
                      "not corporate density.",
        },
        {
            "topic": "Market-value snapshots come from different dates",
            "detail": "Forbes values are May 2025; the scraped Fortune profiles are "
                      "dated 2026. They are never plotted on the same axis.",
        },
    ]

    return {"key": KEY, "metrics": metrics, "tables": tables}


def insights(m: dict) -> list[str]:
    out: list[str] = []

    ag = m.get("agreement_forbes_vs_listed")
    if ag:
        out.append(
            f"**Forbes vs SEC filings.** Across {ag['pairs']:,} companies in both, "
            f"revenue differs by a median of {ag['median_abs_pct_diff']:.1f}%; "
            f"{ag['share_within_10pct']:.0f}% agree to within 10% and "
            f"{ag['share_over_2x']:.0f}% differ by more than 2×."
        )
    ag2 = m.get("agreement_forbes_vs_wiki")
    if ag2:
        out.append(
            f"**Forbes vs Wikipedia country lists.** Across {ag2['pairs']:,} shared "
            f"companies the median revenue gap is {ag2['median_abs_pct_diff']:.1f}% "
            f"and {ag2['share_within_25pct']:.0f}% land within 25% — the Wikipedia "
            f"top-up is usable, but it is a third-tier source and is labelled as such."
        )
    ms = m.get("missingness_summary") or []
    if ms:
        worst = sorted(ms, key=lambda r: -r["cell_missing_pct"])[:3]
        out.append(
            "**Completeness is uneven.** Densest gaps: "
            + ", ".join(
                f"{w['dataset']} ({w['cell_missing_pct']:.0f}% of cells empty, worst "
                f"column `{w['worst_column']}`)" for w in worst
            )
            + "."
        )
    cf = m.get("confidence")
    if cf:
        out.append(
            f"**Every company carries a confidence score** (median "
            f"{cf['median']:.2f}, 10th percentile {cf['p10']:.2f}), derived from "
            f"source trust, how many independent lists corroborate the company, "
            f"and field completeness."
        )
    ov = m.get("wiki_forbes_overlap")
    if ov:
        out.append(
            f"**The Wikipedia top-up mostly finds companies Forbes missed.** "
            f"{ov['wiki_only']:,} of its {ov['wiki_companies']:,} companies are absent "
            f"from the Forbes 2,000 — which is precisely the coverage gap the "
            f"reconciled ranking is built to close."
        )
    out.append(
        "**Read the caveats panel before quoting any single number.** Revenue is a "
        "flow, not value added; valuations are marks, not prices; and the vintage "
        "of every series differs."
    )
    return out
