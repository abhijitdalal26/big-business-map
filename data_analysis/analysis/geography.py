"""Module 2 -- Geography: where the firms are, and where the map lies.

The interesting question is not "which country has the most big companies"
(the United States, obviously) but "does a country's roster of giants match
its economic weight?" A country that is 27% of world GDP but 37% of the
world's largest-company revenue is over-represented; one that is 2% of GDP
and 0% of the list is under-represented -- and the reason is usually
political (sanctions, delisting) or structural (state ownership).

The module deliberately computes every table twice:

* **kept separate** -- Forbes alone, exactly as Forbes counts it
* **mixed** -- the same ranking after reconciling Forbes, Fortune, the
  Wikipedia country lists and the listed universe

The gap between those two columns is the finding.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import stats

KEY = "geography"

GDP_IND = "NY.GDP.MKTP.CD"
POP_IND = "SP.POP.TOTL"
LF_IND = "SL.TLF.TOTL.IN"


def _rollup(ctx, df: pd.DataFrame, label: str) -> pd.DataFrame:
    """Aggregate a company frame to one row per country."""
    d = df.copy()
    d["revenue_usd"] = pd.to_numeric(d.get("revenue_usd"), errors="coerce")
    d["profit_usd"] = pd.to_numeric(d.get("profit_usd"), errors="coerce")
    d["market_cap_usd"] = pd.to_numeric(d.get("market_cap_usd"), errors="coerce")
    d["employees"] = pd.to_numeric(d.get("employees"), errors="coerce")
    d = d.dropna(subset=["country_iso3"])

    g = d.groupby("country_iso3").agg(
        companies=("company", "count"),
        revenue_usd=("revenue_usd", "sum"),
        profit_usd=("profit_usd", "sum"),
        market_cap_usd=("market_cap_usd", "sum"),
        employees=("employees", "sum"),
    ).reset_index()

    names = ctx.idx.set_index("iso3")["name"].to_dict()
    regions = ctx.idx.set_index("iso3")["forbes_region"].to_dict()
    g["country"] = g["country_iso3"].map(names)
    g["region"] = g["country_iso3"].map(regions)
    g["profit_margin"] = g["profit_usd"] / g["revenue_usd"].replace(0, np.nan)
    g["revenue_per_employee"] = g["revenue_usd"] / g["employees"].replace(0, np.nan)
    g["view"] = label
    return g


def run(ctx) -> dict:
    forbes = ctx.forbes()
    mixed = ctx.reconciled

    forbes_roll = _rollup(ctx, forbes, "Forbes Global 2000 only")
    mixed_roll = _rollup(ctx, mixed, "All sources reconciled")

    macro = ctx.macro_latest()
    gdp = {}
    if len(macro) and GDP_IND in macro.columns:
        gdp = (macro[["iso3", GDP_IND, POP_IND, LF_IND]]
               .dropna(subset=[GDP_IND])
               .set_index("iso3")
               .to_dict("index"))

    for label, roll in (("forbes", forbes_roll), ("mixed", mixed_roll)):
        roll["gdp_usd"] = roll["country_iso3"].map(lambda i: gdp.get(i, {}).get(GDP_IND))
        roll["population"] = roll["country_iso3"].map(lambda i: gdp.get(i, {}).get(POP_IND))
        roll["labor_force"] = roll["country_iso3"].map(lambda i: gdp.get(i, {}).get(LF_IND))
        roll["revenue_share"] = roll["revenue_usd"] / roll["revenue_usd"].sum()
        roll["gdp_share"] = roll["gdp_usd"] / roll["gdp_usd"].sum()
        roll["index_vs_gdp"] = np.where(
            roll["gdp_share"] > 0, roll["revenue_share"] / roll["gdp_share"].replace(0, np.nan), np.nan)
        roll["revenue_per_gdp"] = np.where(
            roll["gdp_usd"] > 0, roll["revenue_usd"] / roll["gdp_usd"], np.nan)
        roll = roll.sort_values("revenue_usd", ascending=False).reset_index(drop=True)

    metrics: dict = {}

    # -- correlation between economic weight and corporate weight ----------
    def gdp_corr(roll: pd.DataFrame, label: str) -> dict:
        d = roll.dropna(subset=["gdp_usd", "revenue_usd"])
        d = d[d["gdp_usd"] > 0]
        sp = stats.correlation(d["gdp_share"], d["revenue_share"], "spearman")
        pe = stats.correlation(d["gdp_share"], d["revenue_share"], "pearson")
        return {"label": label, "n": int(len(d)),
                "spearman_r": sp["r"], "spearman_p": sp["p"],
                "pearson_r": pe["r"], "pearson_p": pe["p"]}

    metrics["gdp_correlation"] = {
        "forbes": gdp_corr(forbes_roll, "Forbes Global 2000 only"),
        "mixed": gdp_corr(mixed_roll, "All sources reconciled"),
    }

    # -- over / under-indexed countries -----------------------------------
    def index_table(roll: pd.DataFrame) -> pd.DataFrame:
        d = roll[(roll["gdp_share"].notna()) & (roll["gdp_share"] > 0.0005)].copy()
        d = d.sort_values("index_vs_gdp", ascending=False)
        return d

    over = index_table(forbes_roll)
    metrics["over_indexed_forbes"] = over.head(15)[
        ["country", "companies", "revenue_usd", "gdp_usd", "revenue_share",
         "gdp_share", "index_vs_gdp"]].to_dict("records")
    metrics["under_indexed_forbes"] = over.tail(15).sort_values("index_vs_gdp")[
        ["country", "companies", "revenue_usd", "gdp_usd", "revenue_share",
         "gdp_share", "index_vs_gdp"]].to_dict("records")

    # -- regions -----------------------------------------------------------
    def region_table(roll: pd.DataFrame) -> pd.DataFrame:
        d = roll.dropna(subset=["region"]).copy()
        g = d.groupby("region").agg(
            countries=("country_iso3", "nunique"),
            companies=("companies", "sum"),
            revenue_usd=("revenue_usd", "sum"),
            profit_usd=("profit_usd", "sum"),
            market_cap_usd=("market_cap_usd", "sum"),
            employees=("employees", "sum"),
        ).reset_index()
        total_rev = g["revenue_usd"].sum()
        g["revenue_share"] = g["revenue_usd"] / total_rev
        g["profit_margin"] = g["profit_usd"] / g["revenue_usd"].replace(0, np.nan)
        g["revenue_per_employee"] = g["revenue_usd"] / g["employees"].replace(0, np.nan)
        g["countries_count"] = g["countries"]
        return g.sort_values("revenue_usd", ascending=False)

    reg_forbes = region_table(forbes_roll)
    reg_mixed = region_table(mixed_roll)
    metrics["regions"] = {
        "forbes": reg_forbes.to_dict("records"),
        "mixed": reg_mixed.to_dict("records"),
    }

    # -- national concentration -------------------------------------------
    metrics["national_concentration"] = {
        "forbes_hhi": stats.hhi_points(forbes_roll["revenue_usd"]),
        "mixed_hhi": stats.hhi_points(mixed_roll["revenue_usd"]),
        "forbes_top1_share": stats.top_k_share(forbes_roll["revenue_usd"], 1),
        "forbes_top5_share": stats.top_k_share(forbes_roll["revenue_usd"], 5),
        "forbes_top10_share": stats.top_k_share(forbes_roll["revenue_usd"], 10),
        "mixed_top10_share": stats.top_k_share(mixed_roll["revenue_usd"], 10),
        "forbes_gini": stats.gini(forbes_roll["revenue_usd"]),
        "mixed_gini": stats.gini(mixed_roll["revenue_usd"]),
    }

    # -- coverage gaps: where does Forbes have nothing? --------------------
    # The comparison is keyed on ISO3, not on the display name: a country
    # missing from the index would otherwise be treated as "not in Forbes"
    # purely because its name failed to resolve.
    forbes_isos = set(forbes_roll["country_iso3"].dropna())
    mixed_isos = set(mixed_roll["country_iso3"].dropna())
    coverage = forbes_roll[["country_iso3", "country", "companies", "revenue_usd"]].copy()
    coverage["in_mixed"] = coverage["country_iso3"].isin(mixed_isos)

    # Countries present in the mixed view but absent from Forbes' top 2,000.
    gaps = mixed_roll[~mixed_roll["country_iso3"].isin(forbes_isos)].copy()
    # Fall back to the ISO3 code if a display name is unavailable.
    gaps["country"] = gaps["country"].fillna(gaps["country_iso3"])
    metrics["coverage_gaps"] = {
        "countries_in_mixed_not_in_forbes": int(len(gaps)),
        "revenue_in_gaps": float(gaps["revenue_usd"].sum()),
        "largest_gaps": gaps.nlargest(15, "revenue_usd")[
            ["country", "companies", "revenue_usd"]].to_dict("records"),
    }

    # -- world map payload -------------------------------------------------
    map_df = mixed_roll.copy()
    map_df["revenue_musd"] = map_df["revenue_usd"] / 1e6
    map_df["profit_musd"] = map_df["profit_usd"] / 1e6
    map_df["market_cap_musd"] = map_df["market_cap_usd"] / 1e6
    map_payload = map_df[["country_iso3", "country", "region", "companies",
                          "revenue_musd", "profit_musd", "market_cap_musd",
                          "employees", "profit_margin"]].copy()
    map_payload = map_payload.replace({np.nan: None})

    tables = {
        "country_forbes": forbes_roll,
        "country_mixed": mixed_roll,
        "regions_forbes": reg_forbes,
        "regions_mixed": reg_mixed,
        "map": map_payload,
        "over_under": index_table(forbes_roll)[
            ["country", "companies", "revenue_usd", "gdp_usd", "revenue_share",
             "gdp_share", "index_vs_gdp"]],
    }

    metrics["map_totals"] = {
        "countries_with_firms": int(len(map_payload)),
        "total_revenue_usd": float(map_payload["revenue_musd"].sum() * 1e6),
    }

    return {"key": KEY, "metrics": metrics, "tables": tables}


def insights(m: dict) -> list[str]:
    cf = m["gdp_correlation"]["forbes"]
    cm = m["gdp_correlation"]["mixed"]
    nc = m["national_concentration"]
    gaps = m["coverage_gaps"]
    out = [
        f"Country size tracks corporate size, but loosely. Across the "
        f"{cf['n']} countries Forbes covers, the correlation between a country's "
        f"share of world GDP and its share of Global-2000 revenue is "
        f"**ρ = {cf['spearman_r']:.2f}** (p = {stats.fmt_p(cf['spearman_p'])}).",

        f"Mixing in the Fortune 500, the Wikipedia country lists and the listed "
        f"universe *raises* that correlation to **ρ = {cm['spearman_r']:.2f}** "
        f"(p = {stats.fmt_p(cm['spearman_p'])}) -- the Forbes list alone was "
        f"distorting the map, and mixing the sources repairs part of the distortion.",

        f"National concentration is extreme. One country holds "
        f"**{nc['forbes_top1_share'] * 100:.1f}%** of the revenue in Forbes' list, "
        f"the top five hold **{nc['forbes_top5_share'] * 100:.1f}%** and the top ten "
        f"**{nc['forbes_top10_share'] * 100:.1f}%**. National HHI on revenue is "
        f"**{nc['forbes_hhi']:.0f}** points (mixed view: {nc['mixed_hhi']:.0f}).",

        f"**{gaps['countries_in_mixed_not_in_forbes']} countries** appear in the mixed "
        f"view with no representative at all in Forbes' 2,000, together worth "
        f"**${gaps['revenue_in_gaps'] / 1e9:.0f}B**. The largest such gaps are "
        + ", ".join(f"{r['country']} (${r['revenue_usd'] / 1e9:.0f}B)"
                    for r in gaps["largest_gaps"][:5]) + ".",
    ]
    return out
