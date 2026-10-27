"""Feature engineering and the reconciled company universe.

Design rule, driven by the brief: *keep data separate when needed, mix it when
needed*. So every company observation is stored once per source with an
explicit ``revenue_basis``, and reconciliation happens in a single, auditable
step (:func:`reconcile`) that documents which source won and why.

Nothing here mutates the source CSVs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import clean
from config import REVENUE_BASIS_PRIORITY

UNIVERSE_COLUMNS = [
    "company", "company_key", "source", "source_group", "list_name",
    "rank_in_source", "country", "country_iso3", "region", "city", "state",
    "sector", "industry", "industry_canon", "ownership",
    "revenue_usd", "profit_usd", "assets_usd", "market_cap_usd", "employees",
    "valuation_usd", "revenue_year", "revenue_basis", "revenue_source",
    "confidence", "notes",
]

# Which sources may be added together without double counting.
# "financials" sources are revenue-bearing and are additive only when a source
# scope says so; "valuation" sources are market caps and never mix with revenue.
SOURCE_GROUPS = {
    "forbes": "financials",
    "fortune": "financials",
    "wiki": "financials",
    "listed": "financials",
    "private": "financials",
    "unicorns": "valuation",
    "startups": "valuation",
    "ai": "valuation",
}

US_STATES = {
    "ala.", "alaska", "ariz.", "ark.", "calif.", "colo.", "conn.", "del.",
    "fla.", "ga.", "hawaii", "idaho", "ill.", "ind.", "iowa", "kan.", "ky.",
    "la.", "md.", "mass.", "mich.", "minn.", "miss.", "mo.", "mont.", "neb.",
    "nev.", "n.h.", "n.j.", "n.m.", "n.y.", "n.c.", "n.d.", "ohio", "okla.",
    "ore.", "pa.", "r.i.", "s.c.", "s.d.", "tenn.", "tex.", "utah", "vt.",
    "va.", "wash.", "w.va.", "wis.", "wyo.",
}


def _blank_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=UNIVERSE_COLUMNS)


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    """Return a column, or an all-NaN column of matching length if absent.

    Sources differ in which optional fields they carry; this keeps the
    standardisers free of ``KeyError`` handling.
    """
    if name in df.columns:
        return df[name]
    return pd.Series(np.nan, index=df.index, dtype=object)


def _finalize(df: pd.DataFrame) -> pd.DataFrame:
    for c in UNIVERSE_COLUMNS:
        if c not in df.columns:
            df[c] = np.nan
    df = df[UNIVERSE_COLUMNS].copy()
    df["company_key"] = df["company"].map(clean.company_key)
    return df.reset_index(drop=True)


# --------------------------------------------------------------------------
# Per-source standardisation
# --------------------------------------------------------------------------
def standardize_forbes(b: dict, idx: pd.DataFrame) -> pd.DataFrame:
    df = b["forbes2000"].copy()
    out = pd.DataFrame({
        "company": df["company"],
        "source": "forbes",
        "source_group": "forbes",
        "list_name": "Forbes Global 2000",
        "rank_in_source": df["rank"],
        "country": df["country"],
        "city": _col(df, "city"),
        "state": _col(df, "state"),
        "sector": _col(df, "sector"),
        "industry": _col(df, "industry"),
        "industry_canon": _col(df, "industry_canon"),
        "ownership": "public",
        "revenue_usd": df["revenue_musd"] * 1e6,
        "profit_usd": df["profits_musd"] * 1e6,
        "assets_usd": df["assets_musd"] * 1e6,
        "market_cap_usd": df["market_value_musd"] * 1e6,
        "employees": df["employees"],
        "revenue_year": 2025,
        "revenue_basis": "forbes",
        "revenue_source": "Forbes Global 2000",
        "confidence": "reported",
    })
    out["country_iso3"] = clean.map_countries(out["country"], idx)
    out["region"] = [clean.region_of(i, idx) for i in out["country_iso3"]]
    return _finalize(out)


def parse_fortune_hq(hq: str) -> tuple[str, str, str]:
    """Split a Fortune headquarters string into (city, state, country name)."""
    if not isinstance(hq, str) or not hq.strip():
        return (None, None, None)
    parts = [p.strip() for p in hq.split(",") if p.strip()]
    if len(parts) == 1:
        return (parts[0], None, None)
    last = parts[-1].lower()
    if last in US_STATES:
        return (parts[0], parts[-1], "United States")
    return (parts[0], None, parts[-1])


def standardize_fortune(b: dict, idx: pd.DataFrame) -> pd.DataFrame:
    df = b["fortune500"].copy()
    labels = b.get("fortune_labels")
    out = pd.DataFrame({
        "company": df["company"],
        "source": "fortune",
        "source_group": "fortune",
        "list_name": "Fortune Global 500",
        "rank_in_source": df["rank"],
        "ownership": df["company_type"],
        "revenue_usd": df["revenues_musd"] * 1e6,
        "profit_usd": df["profits_musd"] * 1e6,
        "market_cap_usd": df["market_value_musd"] * 1e6,
        "employees": df["employees"],
        "revenue_year": 2025,
        "revenue_basis": "fortune",
        "revenue_source": "Fortune Global 500",
        "confidence": "reported",
    })
    parsed = [parse_fortune_hq(h) for h in df["headquarters"]]
    out["city"] = [p[0] for p in parsed]
    out["state"] = [p[1] for p in parsed]
    out["country"] = [p[2] for p in parsed]
    out["country_iso3"] = clean.map_countries(out["country"], idx)
    out["region"] = [clean.region_of(i, idx) for i in out["country_iso3"]]
    out["ticker"] = df["ticker"]

    # Manual ownership labels override Fortune's (mis-labelled) company_type.
    if labels is not None and len(labels):
        lab = labels[labels["ownership"] != "DUPLICATE"]
        own = dict(zip(lab["slug"], lab["ownership"]))
        slug_col = df["slug"].str.lower()
        out["ownership"] = [own.get(s, o) for s, o in zip(slug_col, out["ownership"])]
    out["ownership"] = clean.map_ownership(out["ownership"])
    out["sector"] = [clean.map_sector(i) for i in _col(df, "industry")]
    out["industry"] = _col(df, "industry")
    return _finalize(out.drop(columns=["ticker"], errors="ignore"))


def standardize_listed(b: dict, idx: pd.DataFrame) -> pd.DataFrame:
    df = b["listed"].copy()
    df = df[df["revenue_source"] != "rejected: implausible value"].copy()
    sec = df["revenue_source"].str.contains("SEC", case=False, na=False)
    out = pd.DataFrame({
        "company": df["company"],
        "source": "listed",
        "source_group": "listed",
        "list_name": "Listed universe",
        "ticker_or_slug": df["ticker_or_slug"],
        "country": df["country"],
        "market_cap_usd": df["market_cap_usd"],
        "revenue_usd": df["revenue_usd"],
        "revenue_year": df["revenue_year"],
        "revenue_basis": np.where(sec, "sec_filing", "estimate"),
        "revenue_source": df["revenue_source"],
        "confidence": df["confidence"],
    })
    out["country_iso3"] = clean.map_countries(out["country"], idx)
    out["region"] = [clean.region_of(i, idx) for i in out["country_iso3"]]
    out["profit_usd"] = np.nan
    out["assets_usd"] = np.nan
    out["employees"] = np.nan
    out["ownership"] = "public"
    out["sector"] = "Unclassified"
    out["industry"] = "Unclassified"
    return _finalize(out)


def standardize_private(b: dict, idx: pd.DataFrame) -> pd.DataFrame:
    df = b["private_us"].copy()
    out = pd.DataFrame({
        "company": df["company"],
        "source": "private",
        "source_group": "private",
        "list_name": "Forbes America's Top Private Companies",
        "rank_in_source": df["rank"],
        "country": df["country"],
        "city": _col(df, "city"),
        "state": _col(df, "state"),
        "industry": _col(df, "industry"),
        "ownership": "private",
        "revenue_usd": df["revenue_musd"] * 1e6,
        "employees": df["employees"],
        "revenue_year": 2025,
        "revenue_basis": "forbes",
        "revenue_source": "Forbes Largest Private Companies",
        "confidence": "reported",
    })
    out["country_iso3"] = clean.map_countries(out["country"], idx)
    out["region"] = [clean.region_of(i, idx) for i in out["country_iso3"]]
    out["sector"] = [clean.map_sector(i) for i in _col(df, "industry")]
    out["industry_canon"] = out["sector"]
    return _finalize(out)


def standardize_unicorns(b: dict, idx: pd.DataFrame) -> pd.DataFrame:
    df = b["unicorns"].copy()
    out = pd.DataFrame({
        "company": df["company"],
        "source": "unicorns",
        "source_group": "unicorns",
        "list_name": "CB Insights unicorns",
        "rank_in_source": df["rank"],
        "country": df["country"],
        "city": _col(df, "city"),
        "industry": _col(df, "industry"),
        "ownership": "pe",
        "valuation_usd": df["valuation_busd"] * 1e9,
        "revenue_basis": "none",
        "revenue_source": "CB Insights",
        "confidence": "mark",
        "notes": _col(df, "investors"),
    })
    out["country_iso3"] = clean.map_countries(out["country"], idx)
    out["region"] = [clean.region_of(i, idx) for i in out["country_iso3"]]
    out["sector"] = [clean.map_sector(i) for i in _col(df, "industry")]
    out["industry_canon"] = out["sector"]
    return _finalize(out)


def standardize_ai(b: dict, idx: pd.DataFrame) -> pd.DataFrame:
    df = b["ai_companies"].copy()
    out = pd.DataFrame({
        "company": df["company"],
        "source": "ai",
        "source_group": "ai",
        "list_name": "AI model builders",
        "country": _col(df, "country"),
        "industry": _col(df, "category"),
        "ownership": "private",
        "valuation_usd": _col(df, "valuation_busd_cb") * 1e9,
        "revenue_basis": "none",
        "revenue_source": "compiled",
        "confidence": "mixed",
        "notes": _col(df, "modality"),
    })
    out["country_iso3"] = clean.map_countries(out["country"], idx)
    out["region"] = [clean.region_of(i, idx) for i in out["country_iso3"]]
    out["sector"] = "Technology"
    out["industry_canon"] = "Technology"
    return _finalize(out)


def standardize_wiki(b: dict, idx: pd.DataFrame) -> pd.DataFrame:
    """Normalise the scraped Wikipedia country lists."""
    df = b.get("wiki_countries")
    if df is None or not len(df):
        return _blank_frame()
    df = df.copy()
    out = pd.DataFrame({
        "company": df["company"],
        "source": "wiki",
        "source_group": "wiki",
        "list_name": df["list_page"],
        "rank_in_source": _col(df, "rank_in_page"),
        "country": _col(df, "country"),
        "city": _col(df, "headquarters"),
        "industry": _col(df, "industry"),
        "ownership": _col(df, "ownership"),
        "revenue_usd": _col(df, "revenue_usd"),
        "profit_usd": _col(df, "profit_usd"),
        "assets_usd": _col(df, "assets_usd"),
        "market_cap_usd": _col(df, "market_cap_usd"),
        "employees": _col(df, "employees"),
        "revenue_year": _col(df, "data_year"),
        "revenue_basis": "wikipedia",
        "revenue_source": _col(df, "source_table"),
        "confidence": "reported",
        "notes": _col(df, "forbes2000_rank_note"),
    })
    out["country_iso3"] = clean.map_countries(out["country"], idx)
    out["region"] = [clean.region_of(i, idx) for i in out["country_iso3"]]
    out["sector"] = [clean.map_sector(i) for i in out.get("industry", pd.Series(dtype=str))]
    out["industry_canon"] = out["sector"]
    out["ownership"] = clean.map_ownership(out["ownership"].fillna("unknown"))
    return _finalize(out)


# --------------------------------------------------------------------------
# Assembly & reconciliation
# --------------------------------------------------------------------------
def build_universe(b: dict, idx: pd.DataFrame) -> pd.DataFrame:
    """All source observations stacked into one long frame."""
    parts = [
        standardize_forbes(b, idx),
        standardize_fortune(b, idx),
        standardize_listed(b, idx),
        standardize_private(b, idx),
        standardize_unicorns(b, idx),
        standardize_ai(b, idx),
        standardize_wiki(b, idx),
    ]
    parts = [p for p in parts if len(p)]
    if not parts:
        return _blank_frame()
    uni = pd.concat(parts, ignore_index=True)
    # De-duplicate within a source only. rank_in_source keeps two genuinely
    # distinct firms apart when their names normalise to the same key.
    uni = uni.drop_duplicates(
        subset=["company_key", "source", "revenue_basis", "rank_in_source"])
    return uni.reset_index(drop=True)


def scope(uni: pd.DataFrame, sources: list[str] | str | None = None,
          groups: list[str] | None = None) -> pd.DataFrame:
    """Filter the universe to a set of sources or source groups.

    This is the "keep data separate when needed" primitive: every per-source
    statistic in the report is computed on a scoped view of the long frame,
    never on a silently mixed one.
    """
    df = uni
    if sources:
        if isinstance(sources, str):
            sources = [sources]
        df = df[df["source"].isin(sources)]
    if groups:
        df = df[df["source_group"].isin(groups)]
    return df


def reconcile(uni: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Collapse source observations into one row per company.

    Rules
    -----
    * Revenue (and every other financial field) is taken from the single
      highest-priority basis available, never summed.
    * ``sources`` records every source that carried the company, so coverage
      can be audited.
    * ``basis_conflicts`` counts companies where two sources disagreed on
      revenue by more than 20%.

    Returns (reconciled, conflicts).
    """
    if not len(uni):
        return uni.copy(), pd.DataFrame()

    prio = {b: i for i, b in enumerate(REVENUE_BASIS_PRIORITY)}
    work = uni.copy()
    work["_prio"] = work["revenue_basis"].map(prio).fillna(99)
    work = work.sort_values(["company_key", "_prio"])

    grouped = work.groupby("company_key", sort=False)
    first = grouped.first()
    agg = pd.DataFrame(index=first.index)
    agg["sources"] = grouped["source"].agg(lambda s: "|".join(sorted(set(s))))
    agg["n_sources"] = grouped["source"].nunique()
    agg["revenue_conflict"] = grouped["revenue_usd"].agg(
        lambda s: bool(s.notna().sum() > 1
                       and s.max() / max(s.min(), 1e-9) > 1.2))

    keep = ["company", "source", "source_group", "list_name", "rank_in_source",
            "country", "country_iso3", "region", "city", "state", "sector",
            "industry", "industry_canon", "ownership", "revenue_usd",
            "profit_usd", "assets_usd", "market_cap_usd", "employees",
            "valuation_usd", "revenue_year", "revenue_basis", "revenue_source",
            "confidence", "notes"]
    out = pd.concat([first[keep], agg], axis=1).reset_index()

    # Membership flags let the dashboard filter "companies that also appear in
    # the Forbes list" without re-deriving the joins in the browser.
    for src in ("forbes", "fortune", "listed", "wiki", "private", "unicorns",
                "ai"):
        out[f"in_{src}"] = out["sources"].str.split("|").map(
            lambda parts, s=src: s in parts)

    # Prefer the richest ownership label available.
    own_rank = {"state": 0, "mutual": 1, "pe": 2, "public": 3, "private": 4,
                "unknown": 5}
    best_own = (work.assign(_o=work["ownership"].map(own_rank).fillna(9))
                    .sort_values(["company_key", "_o"])
                    .groupby("company_key")["ownership"].first())
    out["ownership"] = out["company_key"].map(best_own).fillna("unknown")

    conflicts = out.loc[out["revenue_conflict"], [
        "company", "sources", "revenue_usd", "revenue_basis", "country_iso3",
        "revenue_conflict"]].copy()
    return out, conflicts


def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Attach the standard financial ratios used across the analysis."""
    d = df.copy()
    rev = d["revenue_usd"]
    d["profit_margin_pct"] = np.where(rev > 0, d["profit_usd"] / rev * 100, np.nan)
    d["roa_pct"] = np.where(d["assets_usd"] > 0, d["profit_usd"] / d["assets_usd"] * 100, np.nan)
    d["asset_turnover"] = np.where(d["assets_usd"] > 0, rev / d["assets_usd"], np.nan)
    d["revenue_per_employee"] = np.where(d["employees"] > 0, rev / d["employees"], np.nan)
    d["profit_per_employee"] = np.where(d["employees"] > 0, d["profit_usd"] / d["employees"], np.nan)
    d["market_cap_to_revenue"] = np.where(rev > 0, d["market_cap_usd"] / rev, np.nan)
    d["market_cap_to_profit"] = np.where(d["profit_usd"] > 0,
                                         d["market_cap_usd"] / d["profit_usd"], np.nan)
    d["log_revenue"] = np.log(d["revenue_usd"].where(d["revenue_usd"] > 0))
    d["log_assets"] = np.log(d["assets_usd"].where(d["assets_usd"] > 0))
    d["log_market_cap"] = np.log(d["market_cap_usd"].where(d["market_cap_usd"] > 0))
    d["is_loss"] = d["profit_usd"].notna() & (d["profit_usd"] < 0)
    d["has_revenue"] = d["revenue_usd"].notna() & (d["revenue_usd"] > 0)
    return d


def company_country_table(df: pd.DataFrame, idx: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the reconciled universe to one row per country."""
    g = df.groupby("country_iso3", dropna=True)
    out = pd.DataFrame({
        "companies": g.size(),
        "revenue_usd": g["revenue_usd"].sum(min_count=1),
        "profit_usd": g["profit_usd"].sum(min_count=1),
        "assets_usd": g["assets_usd"].sum(min_count=1),
        "market_cap_usd": g["market_cap_usd"].sum(min_count=1),
        "employees": g["employees"].sum(min_count=1),
        "valuation_usd": g["valuation_usd"].sum(min_count=1),
    }).reset_index()
    meta = idx[["iso3", "name", "forbes_region"]].rename(
        columns={"iso3": "country_iso3", "name": "country_name",
                 "forbes_region": "region"})
    out = out.merge(meta, on="country_iso3", how="left")
    out["profit_margin_pct"] = np.where(out["revenue_usd"] > 0,
                                        out["profit_usd"] / out["revenue_usd"] * 100,
                                        np.nan)
    out["revenue_per_employee"] = np.where(out["employees"] > 0,
                                           out["revenue_usd"] / out["employees"], np.nan)
    return out.sort_values("revenue_usd", ascending=False).reset_index(drop=True)


__all__ = [
    "UNIVERSE_COLUMNS", "SOURCE_GROUPS", "build_universe", "reconcile", "scope",
    "add_derived_metrics", "company_country_table", "parse_fortune_hq",
    "standardize_forbes", "standardize_fortune", "standardize_listed",
    "standardize_private", "standardize_unicorns", "standardize_ai",
    "standardize_wiki",
]
