"""Module 3 -- Industry: what these firms do, and how they make money.

The central mechanical insight here is that return on assets factors
exactly into two things:

    ROA = net margin x asset turnover

A high-ROA firm is either a *margin* business (software: low assets, fat
margin) or a *turnover* business (retail, food: fat margins on assets but
thin margins per sale). Splitting the two tells you what kind of company
you are looking at, and it is the difference between "profitable business"
and "profitable business model".

We also test whether scale buys profitability, with a log-log regression
that controls for sector and clusters standard errors by country (so a
country with 600 firms is not treated as 600 independent observations).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import models
import stats

KEY = "industry"


def _sector_table(df: pd.DataFrame, by: str) -> pd.DataFrame:
    d = df.copy()
    d["revenue_usd"] = pd.to_numeric(d.get("revenue_usd"), errors="coerce")
    d["profit_usd"] = pd.to_numeric(d.get("profit_usd"), errors="coerce")
    d["assets_usd"] = pd.to_numeric(d.get("assets_usd"), errors="coerce")
    d["market_cap_usd"] = pd.to_numeric(d.get("market_cap_usd"), errors="coerce")
    d["employees"] = pd.to_numeric(d.get("employees"), errors="coerce")

    g = d.groupby(by).agg(
        companies=("company", "count"),
        revenue_usd=("revenue_usd", "sum"),
        profit_usd=("profit_usd", "sum"),
        assets_usd=("assets_usd", "sum"),
        market_cap_usd=("market_cap_usd", "sum"),
        employees=("employees", "sum"),
    ).reset_index()

    g["profit_margin"] = g["profit_usd"] / g["revenue_usd"].replace(0, np.nan)
    g["roa"] = g["profit_usd"] / g["assets_usd"].replace(0, np.nan)
    g["asset_turnover"] = g["revenue_usd"] / g["assets_usd"].replace(0, np.nan)
    g["revenue_per_employee"] = g["revenue_usd"] / g["employees"].replace(0, np.nan)
    g["profit_per_employee"] = g["profit_usd"] / g["employees"].replace(0, np.nan)
    g["market_cap_to_revenue"] = g["market_cap_usd"] / g["revenue_usd"].replace(0, np.nan)
    g["market_cap_to_profit"] = g["market_cap_usd"] / g["profit_usd"].replace(0, np.nan)
    total_rev = g["revenue_usd"].sum()
    g["revenue_share"] = g["revenue_usd"] / total_rev if total_rev else np.nan
    total_profit = g["profit_usd"].sum()
    g["profit_share"] = g["profit_usd"] / total_profit if total_profit else np.nan
    g["roa_check"] = g["profit_margin"] * g["asset_turnover"]
    return g.sort_values("revenue_usd", ascending=False).reset_index(drop=True)


def run(ctx) -> dict:
    forbes = ctx.forbes()
    d = forbes.copy()
    d["revenue_usd"] = pd.to_numeric(d.get("revenue_usd"), errors="coerce")
    d["profit_usd"] = pd.to_numeric(d.get("profit_usd"), errors="coerce")
    d["assets_usd"] = pd.to_numeric(d.get("assets_usd"), errors="coerce")
    d["employees"] = pd.to_numeric(d.get("employees"), errors="coerce")
    d["market_cap_usd"] = pd.to_numeric(d.get("market_cap_usd"), errors="coerce")
    d = d[d["revenue_usd"] > 0]
    # The universe carries `profit_margin_pct`; the sector table works in
    # `profit_margin`. Recompute here so both names agree, and drop the
    # arithmetically impossible cases (profit > revenue) that come from
    # holding-company equity income and partial-period SEC extractions.
    d["profit_margin"] = d["profit_usd"] / d["revenue_usd"] * 100.0
    d.loc[d["profit_margin"].abs() > 100, "profit_margin"] = np.nan

    metrics: dict = {}

    sector_tbl = _sector_table(d, "sector")
    industry_tbl = _sector_table(d, "industry_canon")
    metrics["sector_count"] = int(len(sector_tbl))
    metrics["industry_count"] = int(len(industry_tbl))
    metrics["sector_revenue_total"] = float(sector_tbl["revenue_usd"].sum())
    metrics["sector_profit_total"] = float(sector_tbl["profit_usd"].sum())
    metrics["sector_profit_pool_top5"] = sector_tbl.nlargest(5, "profit_usd")[
        ["sector", "profit_usd", "profit_share"]].to_dict("records")

    # -- ROA decomposition: margin business or turnover business? --------
    deg = sector_tbl.dropna(subset=["roa", "profit_margin", "asset_turnover"]).copy()
    deg["roa_median"] = deg["roa"]
    deg["kind"] = np.where(
        (deg["profit_margin"] >= deg["profit_margin"].median()) &
        (deg["asset_turnover"] >= deg["asset_turnover"].median()), "margin-driven",
        np.where((deg["profit_margin"] < deg["profit_margin"].median()) &
                 (deg["asset_turnover"] >= deg["asset_turnover"].median()),
                 "turnover-driven", "compressed"))
    metrics["roa_decomposition"] = deg[
        ["sector", "profit_margin", "asset_turnover", "roa", "roa_check", "kind"]
    ].to_dict("records")
    metrics["roa_identity_max_error"] = float(
        (deg["roa_check"] - deg["roa"]).abs().max()) if len(deg) else float("nan")

    # -- margin dispersion inside each sector ------------------------------
    # Margin dispersion and the loss rate share one denominator: the firms in
    # the sector that actually report a usable margin. Computing the loss
    # rate over a differently filtered frame would mix two populations.
    dd = d.dropna(subset=["profit_margin"])
    disp = (dd.groupby("sector")["profit_margin"]
            .agg(firms="count", mean="mean", median="median",
                 p10=lambda s: s.quantile(0.10),
                 p90=lambda s: s.quantile(0.90),
                 std="std")
            .reset_index())
    disp["iqr"] = disp["p90"] - disp["p10"]
    disp["cv"] = disp["std"] / disp["mean"].replace(0, np.nan)
    loss = (dd.assign(loss=dd["profit_usd"] < 0)
            .groupby("sector")["loss"]
            .agg(loss_makers="sum")
            .reset_index())
    disp = disp.merge(loss, on="sector", how="left")
    disp["loss_makers"] = disp["loss_makers"].fillna(0)
    disp["loss_rate"] = disp["loss_makers"] / disp["firms"].replace(0, np.nan)
    metrics["margin_dispersion"] = disp.sort_values("median", ascending=False).to_dict("records")

    # -- productivity frontier ---------------------------------------------
    prod = d.dropna(subset=["revenue_per_employee"]).copy()
    prod = prod[prod["employees"] > 0]
    prod["revenue_per_employee"] = prod["revenue_usd"] / prod["employees"]
    metrics["productivity"] = {
        "median_revenue_per_employee": float(prod["revenue_per_employee"].median()),
        "p90": float(prod["revenue_per_employee"].quantile(0.90)),
        "p99": float(prod["revenue_per_employee"].quantile(0.99)),
        "max": float(prod["revenue_per_employee"].max()),
        "ratio_max_median": float(
            prod["revenue_per_employee"].max() / prod["revenue_per_employee"].median()),
        "top_employers": prod.nlargest(15, "employees")[
            ["company", "country", "sector", "employees", "revenue_per_employee"]
        ].to_dict("records"),
        "most_productive": prod.nlargest(15, "revenue_per_employee")[
            ["company", "country", "sector", "employees", "revenue_per_employee"]
        ].to_dict("records"),
    }

    # -- does scale buy profitability? ------------------------------------
    reg = models.ols(
        d.dropna(subset=["profit_margin", "revenue_usd"]),
        y="profit_margin", x_cols=["log_revenue"], categorical=["sector"])
    metrics["margin_on_scale_model"] = {
        "ok": bool(reg.get("ok")),
        "n": reg.get("n"),
        "r2": reg.get("r2"),
        "log_revenue_coef": float(reg["params"].loc[
            reg["params"]["term"] == "log_revenue", "coef"].iloc[0]) if reg.get("ok") else float("nan"),
        "log_revenue_p": float(reg["params"].loc[
            reg["params"]["term"] == "log_revenue", "p"].iloc[0]) if reg.get("ok") else float("nan"),
    }

    # -- valuation by sector -----------------------------------------------
    val = d.dropna(subset=["market_cap_usd"]).copy()
    val["market_cap_to_revenue"] = val["market_cap_usd"] / val["revenue_usd"]
    metrics["valuation_by_sector"] = (
        val.groupby("sector")
        .agg(firms=("company", "count"),
             median_ps=("market_cap_to_revenue", "median"),
             revenue=("revenue_usd", "sum"),
             market_cap=("market_cap_usd", "sum"))
        .reset_index()
        .sort_values("median_ps", ascending=False)
        .to_dict("records"))

    # -- the industry's own concentration ----------------------------------
    conc = []
    for sector, grp in d.groupby("sector"):
        r = grp["revenue_usd"].dropna()
        if len(r) < 5:
            continue
        conc.append({
            "sector": sector,
            "firms": int(len(r)),
            "hhi": stats.hhi_points(r),
            "top5_share": stats.top_k_share(r, 5),
            "gini": stats.gini(r),
        })
    metrics["sector_concentration"] = pd.DataFrame(conc).sort_values(
        "hhi", ascending=False).to_dict("records")

    tables = {
        "sectors": sector_tbl,
        "industries": industry_tbl,
        "margin_dispersion": disp,
        "valuation_by_sector": pd.DataFrame(metrics["valuation_by_sector"]),
        "sector_concentration": pd.DataFrame(metrics["sector_concentration"]),
    }

    return {"key": KEY, "metrics": metrics, "tables": tables}


def insights(m: dict) -> list[str]:
    out = []
    pool = m["sector_profit_pool_top5"]
    if pool:
        out.append(
            "Profit is pooled far more unevenly than revenue. "
            + "; ".join(f"**{r['sector']}** takes {r['profit_share'] * 100:.1f}% "
                        f"(${r['profit_usd'] / 1e9:.0f}B)" for r in pool) + ".")

    deg = m.get("roa_decomposition", [])
    if deg:
        margin_driven = [r["sector"] for r in deg if r["kind"] == "margin-driven"]
        turnover_driven = [r["sector"] for r in deg if r["kind"] == "turnover-driven"]
        out.append(
            f"ROA is exactly margin x turnover (largest identity error "
            f"{m['roa_identity_max_error']:.2e}), and it splits the map in two. "
            f"**Margin-driven** sectors: {', '.join(margin_driven)}. "
            f"**Turnover-driven** sectors: {', '.join(turnover_driven)}.")

    p = m["productivity"]
    out.append(
        f"Productivity per employee spans four orders of magnitude: the median firm "
        f"earns **${p['median_revenue_per_employee'] / 1e6:.1f}M** per head, the 99th "
        f"percentile **${p['p90'] / 1e6:.0f}M**, and the top firm "
        f"**{p['ratio_max_median']:.0f}x** the median.")

    disp = m.get("margin_dispersion", [])
    if disp:
        worst = max(disp, key=lambda r: r.get("loss_rate", 0))
        best = max(disp, key=lambda r: r.get("median", -9e9))
        out.append(
            f"**{worst['sector']}** has the highest rate of loss-making firms "
            f"({worst['loss_rate'] * 100:.0f}% of {int(worst['firms'])} firms), while "
            f"**{best['sector']}** has the highest median net margin "
            f"({best['median']:.1f}%).")

    mod = m.get("margin_on_scale_model", {})
    if mod.get("ok"):
        sig = "significant" if mod["log_revenue_p"] < 0.05 else "not significant"
        # The coefficient is per unit of *natural log* revenue, so it must be
        # multiplied by ln(1.01) to speak about a 1% larger revenue base.
        per_pct = mod["log_revenue_coef"] * np.log(1.01)
        out.append(
            f"Does being bigger make you more profitable? Controlling for sector, a "
            f"1% larger revenue base is associated with "
            f"**{per_pct:.3f} pp** higher net margin "
            f"(p = {stats.fmt_p(mod['log_revenue_p'])}, {sig}; n = {mod['n']:,}).")
    return out
