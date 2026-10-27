"""Loading and schema validation for every dataset in the project.

`load_all()` returns a :class:`Bundle` — one place where every frame lives, so
analysis modules never reach for the filesystem themselves.
"""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from config import REGISTRY, REGISTRY_BY_KEY, SCRAPED


@dataclass
class Bundle:
    """Every dataset, keyed by registry key."""

    frames: dict[str, pd.DataFrame] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def __getitem__(self, key: str) -> pd.DataFrame:
        if key not in self.frames:
            raise KeyError(
                f"'{key}' not loaded. Available: {sorted(self.frames)}")
        return self.frames[key]

    def get(self, key: str, default=None):
        return self.frames.get(key, default)

    def has(self, key: str) -> bool:
        return key in self.frames


EXPECTED_COLUMNS: dict[str, list[str]] = {
    "forbes2000": ["rank", "company", "country", "region", "industry",
                   "revenue_musd", "profits_musd", "assets_musd",
                   "market_value_musd", "employees", "sector", "industry_canon"],
    "fortune500": ["rank", "company", "slug", "headquarters", "company_type",
                   "ticker", "revenues_musd", "profits_musd", "market_value_musd",
                   "employees"],
    "fortune_labels": ["slug", "ownership"],
    "master": ["company", "source", "ownership", "country", "sector",
               "revenue_musd", "profits_musd", "market_value_musd", "employees"],
    "industry_taxonomy": ["sector", "industry_canon", "companies",
                          "revenue_musd", "profits_musd"],
    "country_meta": ["iso3", "name", "region"],
    "country_gdp": ["iso3", "year", "gdp_usd", "country"],
    "world_macro": ["indicator", "indicator_name", "year", "value"],
    "private_us": ["rank", "company", "country", "industry", "revenue_musd",
                   "employees"],
    "forbes_startups": ["list", "company", "country", "industry",
                        "valuation_musd", "funding_musd", "employees"],
    "listed": ["company", "ticker_or_slug", "country", "market_cap_usd",
               "revenue_usd", "revenue_year", "revenue_source", "confidence"],
    "profiles": ["company", "ticker_or_slug", "country", "revenue_usd",
                 "market_cap_usd", "description", "description_source"],
    "exchanges": ["exchange", "exchange_country", "city", "companies",
                  "total_market_cap_usd", "top10_market_cap_usd"],
    "exchange_top": ["exchange", "company", "ticker", "market_cap_usd",
                     "revenue_usd", "rank_in_exchange"],
    "exchange_all": ["exchange", "company", "ticker", "market_cap_usd",
                     "revenue_usd", "rank_in_exchange"],
    "exchange_lookup": ["suffix", "exchange", "country", "city"],
    "unicorns": ["rank", "company", "valuation_busd", "country", "city",
                 "industry", "investors"],
    "startups_global": ["company", "valuation_busd", "country", "city",
                        "industry", "forbes_list"],
    "ai_companies": ["company", "modality", "category", "country", "founded",
                     "status", "open_weights", "hf_org", "valuation_busd_cb"],
    "ai_labs": ["lab", "hf_org", "country", "category", "open_weights",
                "hf_models", "hf_top_downloads", "valuation_busd_cb"],
    "hf_stats": ["hf_org", "hf_models", "hf_top_model", "hf_top_downloads"],
    "forbes2000_hist": ["company", "country", "industry", "metric",
                        "years_ago", "approx_year", "value", "unit"],
}


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def load_all(verbose: bool = True) -> Bundle:
    """Load every registered dataset, validating expected columns."""
    bundle = Bundle()
    for ds in REGISTRY:
        if not ds.path.exists():
            bundle.missing.append(ds.key)
            bundle.notes.append(f"{ds.key}: file not found at {ds.path}")
            continue
        try:
            df = _read(ds.path)
        except Exception as exc:                       # pragma: no cover
            bundle.missing.append(ds.key)
            bundle.notes.append(f"{ds.key}: failed to read ({exc})")
            continue

        expected = EXPECTED_COLUMNS.get(ds.key, [])
        missing_cols = [c for c in expected if c not in df.columns]
        if missing_cols:
            bundle.notes.append(
                f"{ds.key}: missing expected columns {missing_cols}")
        bundle.frames[ds.key] = df

    # Scraped artefacts are optional: the pipeline degrades gracefully.
    for key, path in SCRAPED.items():
        if not path.exists():
            bundle.notes.append(f"{key}: not fetched yet ({path.name})")
            continue
        try:
            if path.suffix == ".csv":
                bundle.frames[key] = _read(path)
            elif path.suffix == ".geojson":
                with open(path, encoding="utf-8") as fh:
                    bundle.frames[key] = json.load(fh)
        except Exception as exc:                       # pragma: no cover
            bundle.notes.append(f"{key}: failed to read ({exc})")

    if verbose:
        for key, df in bundle.frames.items():
            shape = f"{len(df):>7,} rows"
            print(f"  {key:22s} {shape}")
        if bundle.notes:
            print("  -- notes --")
            for n in bundle.notes:
                print(f"     {n}")
    return bundle


def frame_summary(bundle: Bundle) -> pd.DataFrame:
    """One row per dataset: size, coverage and missingness summary."""
    rows = []
    for key, df in bundle.frames.items():
        if not isinstance(df, pd.DataFrame):
            continue
        cells = df.size
        nulls = int(df.isna().sum().sum())
        meta = REGISTRY_BY_KEY.get(key)
        rows.append({
            "dataset": key,
            "label": meta.label if meta else key,
            "trust": meta.trust if meta else "n/a",
            "kind": meta.kind if meta else "n/a",
            "rows": len(df),
            "cols": df.shape[1],
            "null_pct": round(100 * nulls / cells, 2) if cells else 0.0,
        })
    return pd.DataFrame(rows).sort_values("rows", ascending=False)


def missingness_matrix(bundle: Bundle, max_datasets: int = 12) -> pd.DataFrame:
    """Per-column null share for the largest frames."""
    frames = {k: v for k, v in bundle.frames.items()
              if isinstance(v, pd.DataFrame) and len(v) > 0}
    ordered = sorted(frames, key=lambda k: -len(frames[k]))[:max_datasets]
    cols = ["dataset", "column", "non_null", "null_pct", "dtype"]
    out = []
    for key in ordered:
        df = frames[key]
        for c in df.columns:
            s = df[c]
            nn = int(s.notna().sum())
            out.append({
                "dataset": key,
                "column": c,
                "non_null": nn,
                "null_pct": round(100 * (1 - nn / len(s)), 2) if len(s) else 0.0,
                "dtype": str(s.dtype),
            })
    return pd.DataFrame(out, columns=cols)


def to_records(df: pd.DataFrame, limit: int | None = None) -> list[dict]:
    """JSON-safe records for the dashboard."""
    if limit is not None:
        df = df.head(limit)
    df = df.copy()
    for c in df.columns:
        if pd.api.types.is_float_dtype(df[c]):
            df[c] = df[c].round(6)
        elif df[c].dtype == object:
            df[c] = df[c].map(lambda v: None if pd.isna(v) else str(v))
    df = df.replace({np.nan: None})
    return df.to_dict(orient="records")


__all__ = ["Bundle", "load_all", "frame_summary", "missingness_matrix",
           "to_records", "EXPECTED_COLUMNS"]
