"""The analysis context: one object every analysis module receives.

It bundles the raw frames, the harmonised long universe, the reconciled
one-row-per-company view, the country index and the macro panel, and it
exposes the two ways the user asked to see the data:

* **kept separate** -- ``ctx.scope("forbes")``, ``ctx.scope("fortune")`` ...
  one source at a time, exactly as published.
* **mixed** -- ``ctx.reconciled`` and ``ctx.universe``, where the same
  company from different sources has been reconciled into a single row.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

import clean
import features
from io_load import Bundle, load_all


@dataclass
class Context:
    bundle: Bundle
    idx: pd.DataFrame
    universe: pd.DataFrame
    reconciled: pd.DataFrame
    conflicts: pd.DataFrame
    macro: pd.DataFrame = field(default_factory=pd.DataFrame)
    notes: dict = field(default_factory=dict)

    # -- source views ------------------------------------------------------
    def scope(self, source: str | None = None,
              group: str | None = None) -> pd.DataFrame:
        """Filter the long universe to one source or one kind of source."""
        return features.scope(self.universe, sources=[source] if source else None,
                              groups=[group] if group else None)

    def forbes(self) -> pd.DataFrame:
        return self.scope("forbes")

    def fortune(self) -> pd.DataFrame:
        return self.scope("fortune")

    def listed(self) -> pd.DataFrame:
        return self.scope("listed")

    def wiki(self) -> pd.DataFrame:
        return self.scope("wiki")

    def private(self) -> pd.DataFrame:
        return self.scope("private")

    def valuation_only(self) -> pd.DataFrame:
        return self.scope(group="valuation")

    # -- macro -------------------------------------------------------------
    def macro_for(self, year: int) -> pd.DataFrame:
        """Wide macro panel for one year, one row per country."""
        if self.macro is None or not len(self.macro):
            return pd.DataFrame()
        m = self.macro[self.macro["year"] == year]
        if not len(m):
            return pd.DataFrame()
        wide = m.pivot_table(index=["iso3", "country"], columns="indicator",
                             values="value", aggfunc="first")
        return wide.reset_index()

    def macro_latest(self) -> pd.DataFrame:
        """Latest available value per country per indicator."""
        if self.macro is None or not len(self.macro):
            return pd.DataFrame()
        latest = (self.macro.sort_values("year")
                  .groupby(["iso3", "indicator"], as_index=False)
                  .tail(1))
        wide = latest.pivot_table(index=["iso3", "country"], columns="indicator",
                                  values="value", aggfunc="first")
        return wide.reset_index()

    # -- helpers -----------------------------------------------------------
    def country_rollup(self, df: pd.DataFrame | None = None) -> pd.DataFrame:
        """Aggregate any company frame to one row per country."""
        d = self.reconciled if df is None else df
        return features.company_country_table(d, self.idx)

    def iso(self, name: str) -> str | None:
        return clean.country_iso3(name, self.idx)


def build(verbose: bool = True) -> Context:
    """Load every source, harmonise, reconcile, and return the context."""
    bundle = load_all(verbose=verbose)
    notes: dict = {}

    forbes_raw = bundle.get("forbes2000")
    idx = clean.build_country_index(bundle.get("country_meta"), forbes_raw)
    notes["country_index"] = {"rows": int(len(idx)),
                              "unmapped": int(idx["iso3"].isna().sum())}

    universe = features.build_universe(bundle, idx)
    reconciled, conflicts = features.reconcile(universe)
    reconciled = features.add_derived_metrics(reconciled)
    universe = features.add_derived_metrics(universe)

    macro = bundle.get("worldbank_extra")
    if macro is None or not len(macro):
        macro = bundle.get("world_macro")
    if macro is not None and len(macro):
        macro = macro.copy()
        if "iso3" not in macro.columns:
            macro["iso3"] = macro.apply(
                lambda r: clean.country_iso3(r.get("country", ""), idx), axis=1)

    ctx = Context(bundle=bundle, idx=idx, universe=universe,
                  reconciled=reconciled, conflicts=conflicts, macro=macro,
                  notes=notes)
    if verbose:
        print(f"  context ready: universe {len(universe):,} rows, "
              f"reconciled {len(reconciled):,} companies, "
              f"conflicts {len(conflicts):,}")
    return ctx


def main() -> None:
    ctx = build()
    print("\nsources in universe:")
    print(ctx.universe["source"].value_counts().to_string())
    print("\nownership mix (reconciled):")
    print(ctx.reconciled["ownership"].value_counts().to_string())


if __name__ == "__main__":
    main()
