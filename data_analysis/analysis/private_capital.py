"""Module 6 -- Private capital: the part of the economy with no market price.

The Forbes Global 2000 and the Fortune 500 are both lists of *publicly
reportable* companies. The private half of the global firm universe --
family businesses, mutual insurers, state oil companies, venture-backed
giants -- is invisible to them by construction.

This module handles that half, and it is careful about a specific trap:
**a valuation is a mark, a revenue is a fact**. Unicorn "valuations" are
last-round private prices, often years stale, and they are never added to
revenue. Where the report compares a paper number with a real one, both
labels are carried through.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import stats

KEY = "private_capital"


def run(ctx) -> dict:
    metrics: dict = {}

    # -- 1. unicorns --------------------------------------------------------
    uni = ctx.bundle.get("unicorns")
    if uni is not None and len(uni):
        u = uni.copy()
        u["valuation_usd"] = pd.to_numeric(u["valuation_busd"], errors="coerce") * 1e9
        u = u.dropna(subset=["valuation_usd"])
        u["country_iso3"] = u["country"].map(lambda c: ctx.iso(c) or "")
        u["region"] = u["country_iso3"].map(
            lambda i: ctx.idx.loc[ctx.idx["iso3"] == i, "forbes_region"].iloc[0]
            if (ctx.idx["iso3"] == i).any() else "Unknown")

        total_val = float(u["valuation_usd"].sum())
        metrics["unicorns"] = {
            "count": int(len(u)),
            "total_valuation": total_val,
            "median_valuation": float(u["valuation_usd"].median()),
            "mean_valuation": float(u["valuation_usd"].mean()),
            "countries": int(u["country"].nunique()),
            "hhi_by_country": stats.hhi_points(
                u.groupby("country")["valuation_usd"].sum()),
            "gini_by_country": stats.gini(
                u.groupby("country")["valuation_usd"].sum()),
            "top1_country_share": stats.top_k_share(
                u.groupby("country")["valuation_usd"].sum(), 1),
            "top5_country_share": stats.top_k_share(
                u.groupby("country")["valuation_usd"].sum(), 5),
            "distribution": stats.describe(u["valuation_usd"]),
            "top_20": u.nlargest(20, "valuation_usd")[
                ["company", "country", "industry", "valuation_busd", "date_joined"]
            ].to_dict("records"),
            "by_country": u.groupby(["country", "region"]).agg(
                companies=("company", "count"),
                valuation_usd=("valuation_usd", "sum")).reset_index()
            .sort_values("valuation_usd", ascending=False).to_dict("records"),
            "by_industry": u.groupby("industry").agg(
                companies=("company", "count"),
                valuation_usd=("valuation_usd", "sum")).reset_index()
            .sort_values("valuation_usd", ascending=False).to_dict("records"),
        }

        # The wave: when each company crossed $1B.
        if "date_joined" in u.columns:
            joined = pd.to_datetime(u["date_joined"], errors="coerce")
            by_year = u.assign(year=joined.dt.year).groupby("year").agg(
                companies=("company", "count"),
                valuation_usd=("valuation_usd", "sum")).reset_index()
            by_year = by_year.dropna(subset=["year"])
            metrics["unicorns"]["by_year_joined"] = by_year.to_dict("records")

    # -- 2. unlisted revenue pool -------------------------------------------
    # Companies we can measure that have no listed share: Forbes' US private
    # list, plus every unlisted name in the mixed universe.
    priv = ctx.private()
    metrics["private_us_list"] = {
        "count": int(len(priv)),
        "total_revenue": float(pd.to_numeric(
            priv.get("revenue_usd"), errors="coerce").sum()),
        "top_15": priv.nlargest(15, "revenue_usd")[
            ["company", "industry", "revenue_usd", "employees"]].to_dict("records"),
    }

    mixed = ctx.reconciled
    forbes = ctx.forbes()
    forbes_keys = set(forbes["company_key"].dropna())
    unlisted = mixed[mixed["revenue_usd"].notna() & (mixed["revenue_usd"] > 0)].copy()
    unlisted = unlisted[~unlisted["company_key"].isin(forbes_keys)]
    # Exclude anything the listed universe already knows about.
    listed_keys = set(ctx.listed()["company_key"].dropna())
    truly_unlisted = unlisted[~unlisted["company_key"].isin(listed_keys)]
    metrics["unlisted"] = {
        "count": int(len(truly_unlisted)),
        "total_revenue": float(truly_unlisted["revenue_usd"].sum()),
        "by_ownership": truly_unlisted.groupby("ownership").agg(
            firms=("company", "count"),
            revenue_usd=("revenue_usd", "sum")).reset_index()
        .sort_values("revenue_usd", ascending=False).to_dict("records"),
        "top_25": truly_unlisted.nlargest(25, "revenue_usd")[
            ["company", "country", "ownership", "sector", "revenue_usd"]
        ].assign(revenue_musd=lambda x: x["revenue_usd"] / 1e6)[
            ["company", "country", "ownership", "sector", "revenue_musd"]
        ].to_dict("records"),
    }

    # -- 3. AI labs ---------------------------------------------------------
    ai = ctx.bundle.get("ai_companies")
    if ai is not None and len(ai):
        a = ai.copy()
        a["valuation_usd"] = pd.to_numeric(
            a.get("valuation_busd_cb"), errors="coerce") * 1e9
        a["country_iso3"] = a["country"].map(lambda c: ctx.iso(c) or "")
        metrics["ai"] = {
            "count": int(len(a)),
            "by_modality": a["modality"].value_counts().to_dict(),
            "by_openness": a["open_weights"].value_counts().to_dict(),
            "by_country": a["country"].value_counts().to_dict(),
            "by_category": a["category"].value_counts().to_dict(),
            "with_valuation": int(a["valuation_usd"].notna().sum()),
            "total_valuation": float(a["valuation_usd"].sum()),
            "top_15": a.nlargest(15, "valuation_usd")[
                ["company", "country", "modality", "open_weights",
                 "valuation_busd_cb"]].to_dict("records"),
            "open_by_country": pd.crosstab(
                a["country"], a["open_weights"]).reset_index().to_dict("records"),
        }
        # Is the frontier open or closed, by country?
        for country, grp in a.groupby("country"):
            pass
        frontiers = a[a["category"].astype(str).str.contains("Frontier", case=False)]
        if len(frontiers):
            metrics["ai"]["frontier"] = {
                "count": int(len(frontiers)),
                "open_weights": frontiers["open_weights"].value_counts().to_dict(),
                "by_country": frontiers["country"].value_counts().to_dict(),
            }

    labs = ctx.bundle.get("ai_labs")
    if labs is not None and len(labs):
        L = labs.copy()
        L["hf_top_downloads"] = pd.to_numeric(L.get("hf_top_downloads"), errors="coerce")
        metrics["ai_labs"] = {
            "count": int(len(L)),
            "by_openness": L["open_weights"].value_counts().to_dict(),
            "by_country": L["country"].value_counts().to_dict(),
            "top_downloads": L.nlargest(15, "hf_top_downloads")[
                ["lab", "country", "hf_top_model", "hf_top_downloads",
                 "open_weights", "hf_license"]].to_dict("records"),
            "total_downloads_top_model": float(L["hf_top_downloads"].sum()),
        }

    # -- 4. paper economy vs real economy ----------------------------------
    forbes_rev = float(forbes["revenue_usd"].sum())
    listed = ctx.listed()
    listed_mcap = float(pd.to_numeric(
        listed.get("market_cap_usd"), errors="coerce").sum())
    uni_val = metrics.get("unicorns", {}).get("total_valuation", float("nan"))
    metrics["paper_vs_real"] = {
        "forbes_revenue": forbes_rev,
        "listed_market_cap": listed_mcap,
        "unicorn_paper_value": uni_val,
        "unicorn_value_as_pct_of_listed_mcap": (
            uni_val / listed_mcap * 100 if listed_mcap else float("nan")),
        "note": "unicorn value is a private mark; it is not revenue and not a "
                "traded price, and the three numbers are not additive",
    }

    # -- 5. overlap: how much of the private world is already public? ------
    uni_keys = set()
    if uni is not None and len(uni):
        import clean
        uni_keys = set(uni["company"].map(clean.company_key))
    # The unicorn board is itself one of the sources in the reconciled
    # universe, so matching against the whole universe would report a 100%
    # overlap by construction. Match against every *other* source instead:
    # that is the set of unicorns we can also see somewhere else.
    mixed_other = mixed[mixed["source"] != "unicorns"]
    mixed_keys = set(mixed_other["company_key"].dropna())
    metrics["overlap"] = {
        "unicorn_companies": len(uni_keys),
        "unicorns_also_in_reconciled": len(uni_keys & mixed_keys),
        "unicorns_also_in_forbes": len(uni_keys & forbes_keys),
        "note": "A unicorn that also appears in another source has already "
                "IPO'd or been reclassified; the board lags reality.",
    }

    tables = {
        "unicorns_by_country": pd.DataFrame(
            metrics.get("unicorns", {}).get("by_country", [])),
        "unicorns_by_industry": pd.DataFrame(
            metrics.get("unicorns", {}).get("by_industry", [])),
        "unicorns_top": pd.DataFrame(
            metrics.get("unicorns", {}).get("top_20", [])),
        "private_us": priv.nlargest(60, "revenue_usd")[
            ["company", "industry", "revenue_usd", "employees"]],
        "unlisted_top": truly_unlisted.nlargest(100, "revenue_usd")[
            ["company", "country", "ownership", "sector", "revenue_usd"]],
        "unicorns_by_year": pd.DataFrame(
            metrics.get("unicorns", {}).get("by_year_joined", []),
            columns=["year", "companies", "valuation_usd"]),
        "ai_by_modality": pd.DataFrame(
            list(metrics.get("ai", {}).get("by_modality", {}).items()),
            columns=["modality", "companies"]),
    }

    return {"key": KEY, "metrics": metrics, "tables": tables}


def insights(m: dict) -> list[str]:
    out = []
    u = m.get("unicorns")
    if u:
        out.append(
            f"The private tail is enormous and unusually concentrated: "
            f"**{u['count']:,}** unicorns carry **{u['total_valuation'] / 1e12:.2f} T$** of "
            f"paper value across **{u['countries']}** countries, but the top country holds "
            f"**{u['top1_country_share'] * 100:.0f}%** of it and the top five "
            f"**{u['top5_country_share'] * 100:.0f}%** (HHI {u['hhi_by_country']:.0f}). "
            f"The median unicorn is worth **${u['median_valuation'] / 1e9:.1f}B**; the "
            f"mean is **{u['mean_valuation'] / u['median_valuation']:.1f}x** the median.")

    unl = m.get("unlisted")
    if unl:
        out.append(
            f"**{unl['count']:,}** companies with measurable revenue have no listed "
            f"share at all, worth **{unl['total_revenue'] / 1e12:.2f} T$** — real revenue, "
            f"not paper. "
            + "; ".join(f"**{r['ownership']}** accounts for "
                        f"${r['revenue_usd'] / 1e9:.0f}B across {r['firms']} firms"
                        for r in unl["by_ownership"][:3]) + ".")

    ai = m.get("ai")
    if ai:
        fw = ai.get("frontier", {})
        # The dataset codes openness as "yes" / "partial" / "no".
        op = ai.get("by_openness", {})
        out.append(
            f"Among **{ai['count']}** AI model builders, **{op.get('yes', 0)}** "
            f"ship open weights, **{op.get('partial', 0)}** are partial and "
            f"**{op.get('no', 0)}** are closed. At the frontier specifically "
            f"({fw.get('count', 0)} labs) the split is "
            f"{fw.get('open_weights', {})} by country {fw.get('by_country', {})} — "
            f"openness is a regional strategy, not a universal one.")

    pr = m.get("paper_vs_real")
    if pr:
        out.append(
            f"**Keep the ledgers separate.** The Forbes 2,000 report "
            f"**${pr['forbes_revenue'] / 1e12:.1f} T$** of *revenue*; the listed universe "
            f"reports **${pr['listed_market_cap'] / 1e12:.1f} T$** of *market value*; the "
            f"unicorn board reports **${pr['unicorn_paper_value'] / 1e12:.2f} T$** of "
            f"*paper marks* — equal to "
            f"**{pr['unicorn_value_as_pct_of_listed_mcap']:.1f}%** of the listed market. "
            f"These three numbers measure different things and must never be summed.")

    ov = m.get("overlap")
    if ov:
        out.append(
            f"The unicorn board overlaps the public world more than its reputation "
            f"suggests: **{ov['unicorns_also_in_reconciled']:,}** of "
            f"{ov['unicorn_companies']:,} unicorn names also appear in the reconciled "
            f"universe. A $1B+ private mark from an old round is not a current price.")
    return out
