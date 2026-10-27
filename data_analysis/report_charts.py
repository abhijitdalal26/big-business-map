"""Chart generation for the study pack.

Every chart is a small function that pulls a table out of the analysis results,
and returns a record describing the image it produced. Failures are contained:
a chart that cannot be drawn is reported and skipped rather than aborting the
whole report, so one broken panel never costs the reader the other thirty.

The house style lives in ``style.py``; this module only chooses *what* to draw.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

import style as S
from style import (ACCENT, BAR, GRID, INK, MUTED, PALETTE, count_fmt, hbar,
                   money_b, money_m, new_fig, pct_fmt, save, style)

SOURCE_FORBES = "Source: Forbes Global 2000 (2025), company-reported figures."
SOURCE_MIXED = ("Source: Forbes Global 2000, Fortune 500, Wikipedia country "
                "lists, CB Insights, SEC XBRL and companiesmarketcap, "
                "harmonised by the analysis engine.")


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def col(df: pd.DataFrame, *names: str, default: Any = None) -> Any:
    """First matching column of ``df`` (or ``default``)."""
    if df is None or not hasattr(df, "columns"):
        return default
    for n in names:
        if n in df.columns:
            return df[n]
    return default


def num(df: pd.DataFrame, *names: str) -> pd.Series:
    """First matching column coerced to float, or an empty float series."""
    s = col(df, *names, default=None)
    if s is None:
        return pd.Series(dtype="float64")
    return pd.to_numeric(s, errors="coerce")


def frame(obj: Any) -> pd.DataFrame:
    if isinstance(obj, pd.DataFrame):
        return obj
    if isinstance(obj, list):
        return pd.DataFrame(obj)
    return pd.DataFrame()


def diverging_hbar(ax, labels, values, value_fmt=money_b, pad=0.02):
    """Horizontal bars that may run left (negative) or right (positive)."""
    labels = list(labels)
    values = np.asarray(values, dtype=float)
    y = np.arange(len(labels))[::-1]
    colors = [ACCENT if v < 0 else BAR for v in values]
    ax.barh(y, values, color=colors, height=0.68, zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    span = max(abs(values).max(), 1.0) if len(values) else 1.0
    for yi, v in zip(y, values):
        off = span * pad
        ax.text(v + (off if v >= 0 else -off), yi, value_fmt(v),
                va="center", ha="left" if v >= 0 else "right",
                fontsize=8.6, color=INK, zorder=4)
    ax.set_xlim(-span * 1.30, span * 1.30)
    ax.axvline(0, color="#C9D2DD", lw=0.9, zorder=2)
    return ax


def _fmt_billions(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce") / 1e9


def _clean_labels(df: pd.DataFrame, *names: str, default: str = "") -> pd.Series:
    s = col(df, *names, default=None)
    if s is None:
        return pd.Series([default] * len(df), index=df.index)
    return s.astype(str).fillna(default).replace("", default)


# --------------------------------------------------------------------------- #
# chart registry
# --------------------------------------------------------------------------- #
class ChartBook:
    """Collects chart definitions and runs them, tolerating failures."""

    def __init__(self, out_dir: Path) -> None:
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.records: list[dict] = []
        self.failures: list[dict] = []
        self._n = 0
        # Set by the caller before each module's chart function so that every
        # record knows which section of the study pack it belongs to.
        self.current_module: str | None = None

    def add(self, slug: str, title: str, subtitle: str, source: str,
            draw: Callable[[], tuple], caption: str = "") -> None:
        self._n += 1
        num_id = f"{self._n:02d}"
        name = f"{num_id}_{slug}"
        path = self.out_dir / f"{name}.png"
        # The draw() closure needs to know where to write its PNG. It reads
        # the target name back out of the book via _target().
        self._pending = f"{name}.png"
        try:
            draw()
        except Exception as exc:  # noqa: BLE001 - a bad panel must not kill the report
            self.failures.append({
                "chart": name, "error": f"{type(exc).__name__}: {exc}",
            })
            if path.exists():
                path.unlink()
            return
        if not path.exists():
            self.failures.append({
                "chart": name, "error": "draw() produced no file",
            })
            return
        self.records.append({
            "id": num_id, "slug": slug, "title": title, "subtitle": subtitle,
            "module": self.current_module,
            "file": path.name, "path": f"charts/{path.name}",
            "caption": caption or f"{title} — {subtitle}",
        })


# --------------------------------------------------------------------------- #
# scale
# --------------------------------------------------------------------------- #
def charts_scale(book: ChartBook, ctx, res) -> None:
    m = res["metrics"]
    t = res["tables"]
    forbes = ctx.forbes()

    def top_revenue():
        d = forbes.copy()
        d["rev"] = num(d, "revenue_usd", "revenue")
        d = d.dropna(subset=["rev"]).nlargest(20, "rev")
        fig, ax = new_fig(9.2, 6.4)
        labels = _clean_labels(d, "company", "name")
        hbar(ax, labels, _fmt_billions(d["rev"]), highlight=labels.iloc[0]
             if len(labels) else None)
        style(ax, "The twenty largest companies on earth",
              "Revenue, 2025 — Forbes Global 2000", SOURCE_FORBES)
        save(fig, book.out_dir / _target(book), SOURCE_FORBES)

    book.add("top20_revenue", "The twenty largest companies on earth",
             "Revenue, 2025 — Forbes Global 2000", SOURCE_FORBES, top_revenue,
             "Ranked by revenue, the top twenty account for a quarter of all "
             "corporate output measured in the Forbes Global 2000.")

    def thresholds():
        d = frame(t.get("thresholds"))
        d["firms"] = num(d, "firms")
        d = d.dropna(subset=["firms"]).sort_values("firms", ascending=False)
        fig, ax = new_fig(9.2, 4.6)
        labels = [f"≥ {money_b(float(x) / 1e9)}" for x in
                  num(d, "threshold", "revenue_usd")]
        hbar(ax, labels, d["firms"].to_numpy(), value_fmt=count_fmt)
        style(ax, "How many firms clear each revenue bar",
              "Cumulative count of Forbes Global 2000 companies above a "
              "revenue threshold", SOURCE_FORBES)
        save(fig, book.out_dir / _target(book), SOURCE_FORBES)

    book.add("revenue_thresholds", "How many firms clear each revenue bar",
             "Cumulative count above a revenue threshold", SOURCE_FORBES,
             thresholds)

    def zipf():
        d = forbes.copy()
        d["rev"] = num(d, "revenue_usd")
        d = d.dropna(subset=["rev"]).sort_values("rev", ascending=False)
        ranks = np.arange(1, len(d) + 1)
        fig, ax = new_fig(9.2, 5.4)
        ax.scatter(ranks, d["rev"].to_numpy() / 1e9, s=9, color=BAR, alpha=0.55,
                   zorder=3, edgecolors="none")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Rank (log scale)")
        ax.set_ylabel("Revenue, USD billions (log scale)")
        ze = m.get("zipf_revenue", {}) or {}
        style(ax, "The rank-size curve",
              f"Zipf exponent {ze.get('exponent', float('nan')):.2f} · "
              f"R² {ze.get('r2', float('nan')):.3f} — firm size decays smoothly, "
              "not through one dominant tier", SOURCE_FORBES)
        save(fig, book.out_dir / _target(book), SOURCE_FORBES)

    book.add("rank_size_zipf", "The rank-size curve",
             "Revenue against rank, both on a log scale", SOURCE_FORBES, zipf)

    def truncation():
        d = frame(t.get("top_beyond_forbes"))
        d["rev"] = num(d, "revenue_musd")
        d = d.dropna(subset=["rev"]).nlargest(20, "rev")
        fig, ax = new_fig(9.2, 6.2)
        labels = _clean_labels(d, "company")
        hbar(ax, labels, d["rev"].to_numpy(), value_fmt=money_m)
        style(ax, "What Forbes' list leaves out",
              "Largest measured companies that never appear in the Global 2000",
              SOURCE_MIXED)
        save(fig, book.out_dir / _target(book), SOURCE_MIXED)

    book.add("truncation_gap", "What Forbes' list leaves out",
             "Largest measured companies absent from the Global 2000",
             SOURCE_MIXED, truncation)


# --------------------------------------------------------------------------- #
# geography
# --------------------------------------------------------------------------- #
def charts_geography(book: ChartBook, ctx, res) -> None:
    t = res["tables"]

    def top_countries():
        d = frame(t.get("country_mixed")).copy()
        d["rev"] = num(d, "revenue_usd")
        d = d.dropna(subset=["rev"]).nlargest(20, "rev")
        fig, ax = new_fig(9.2, 6.4)
        labels = _clean_labels(d, "country")
        hbar(ax, labels, _fmt_billions(d["rev"]),
             highlight=labels.iloc[0] if len(labels) else None)
        style(ax, "Where the world's corporate revenue is booked",
              "Top 20 countries by measured revenue, all sources reconciled",
              SOURCE_MIXED)
        save(fig, book.out_dir / _target(book), SOURCE_MIXED)

    book.add("top_countries", "Where the world's corporate revenue is booked",
             "Top 20 countries by measured revenue", SOURCE_MIXED, top_countries)

    def rev_vs_gdp():
        d = frame(t.get("over_under")).copy()
        rs = num(d, "revenue_share")
        gs = num(d, "gdp_share")
        ok = rs.notna() & gs.notna() & (gs > 0)
        d = d[ok]
        rs, gs = rs[ok] * 100, gs[ok] * 100
        fig, ax = new_fig(9.2, 6.2)
        ax.scatter(gs, rs, s=46, color=BAR, alpha=0.75, zorder=3,
                   edgecolors="white", linewidths=0.8)
        lim = max(float(rs.max()), float(gs.max())) * 1.15 if len(d) else 1.0
        ax.plot([0, lim], [0, lim], color=MUTED, lw=1.0, ls="--", zorder=2)
        ax.set_xlabel("Share of world GDP (%)")
        ax.set_ylabel("Share of measured corporate revenue (%)")
        for _, r in d.iterrows():
            ax.annotate(str(r.get("country", "")),
                        (float(r["gdp_share"]) * 100, float(r["revenue_share"]) * 100),
                        fontsize=8, color="#4A5563",
                        xytext=(4, 4), textcoords="offset points")
        style(ax, "Corporate weight against economic weight",
              "Above the dashed line: the country hosts more corporate revenue "
              "than its GDP would predict", SOURCE_MIXED)
        save(fig, book.out_dir / _target(book), SOURCE_MIXED)

    book.add("revenue_vs_gdp", "Corporate weight against economic weight",
             "Revenue share against GDP share", SOURCE_MIXED, rev_vs_gdp)

    def regions():
        d = frame(t.get("regions_mixed")).copy()
        d["rev"] = num(d, "revenue_usd")
        d = d.dropna(subset=["rev"]).sort_values("rev", ascending=False)
        fig, ax = new_fig(9.2, 4.8)
        labels = _clean_labels(d, "region")
        hbar(ax, labels, _fmt_billions(d["rev"]))
        style(ax, "Six regions, one world",
              "Measured corporate revenue by region, all sources reconciled",
              SOURCE_MIXED)
        save(fig, book.out_dir / _target(book), SOURCE_MIXED)

    book.add("regions", "Six regions, one world",
             "Measured revenue by region", SOURCE_MIXED, regions)

    def region_compare():
        f = frame(t.get("regions_forbes")).copy()
        mx = frame(t.get("regions_mixed")).copy()
        for d in (f, mx):
            d["share"] = num(d, "revenue_share") * 100
        merged = f[["region", "share"]].merge(
            mx[["region", "share"]], on="region", suffixes=("_f", "_m"))
        merged = merged.sort_values("share_m", ascending=False)
        fig, ax = new_fig(9.2, 4.8)
        x = np.arange(len(merged))
        w = 0.38
        ax.bar(x - w / 2, merged["share_f"], w, label="Forbes Global 2000",
               color=PALETTE[1], zorder=3)
        ax.bar(x + w / 2, merged["share_m"], w, label="All sources reconciled",
               color=PALETTE[4], zorder=3)
        ax.set_xticks(x)
        ax.set_xticklabels(merged["region"], rotation=12, ha="right")
        ax.set_ylabel("Share of measured revenue (%)")
        ax.legend(fontsize=9)
        style(ax, "What mixing in the other lists changes",
              "Regional revenue share, Forbes list only versus the reconciled "
              "universe", SOURCE_MIXED)
        save(fig, book.out_dir / _target(book), SOURCE_MIXED)

    book.add("region_compare", "What mixing in the other lists changes",
             "Forbes-only versus reconciled regional shares", SOURCE_MIXED,
             region_compare)


# --------------------------------------------------------------------------- #
# industry
# --------------------------------------------------------------------------- #
def charts_industry(book: ChartBook, ctx, res) -> None:
    t = res["tables"]

    def sector_rev_profit():
        d = frame(t.get("sectors")).copy()
        d["rev"] = num(d, "revenue_usd")
        d["prof"] = num(d, "profit_usd")
        d = d.dropna(subset=["rev"]).sort_values("rev", ascending=False)
        fig, ax = new_fig(9.4, 5.6)
        x = np.arange(len(d))
        w = 0.4
        ax.bar(x - w / 2, d["rev"] / 1e9, w, label="Revenue", color=PALETTE[1],
               zorder=3)
        ax.bar(x + w / 2, d["prof"] / 1e9, w, label="Profit", color=PALETTE[4],
               zorder=3)
        ax.set_xticks(x)
        ax.set_xticklabels(_clean_labels(d, "sector"), rotation=18, ha="right")
        ax.set_ylabel("USD billions")
        ax.legend(fontsize=9)
        style(ax, "Revenue and profit by sector",
              "Profit is far more concentrated than revenue", SOURCE_FORBES)
        save(fig, book.out_dir / _target(book), SOURCE_FORBES)

    book.add("sector_revenue_profit", "Revenue and profit by sector",
             "Where the money comes from, and where it stays", SOURCE_FORBES,
             sector_rev_profit)

    def sector_margin():
        d = frame(t.get("margin_dispersion")).copy()
        d["median"] = num(d, "median")
        d = d.dropna(subset=["median"]).sort_values("median", ascending=False)
        fig, ax = new_fig(9.2, 5.2)
        labels = _clean_labels(d, "sector")
        hbar(ax, labels, d["median"].to_numpy(), value_fmt=pct_fmt)
        style(ax, "Median net margin by sector",
              "Middle firm in each sector, not the average of a few giants",
              SOURCE_FORBES)
        save(fig, book.out_dir / _target(book), SOURCE_FORBES)

    book.add("sector_margin", "Median net margin by sector",
             "The middle firm in each sector", SOURCE_FORBES, sector_margin)

    def dispersion():
        d = frame(t.get("margin_dispersion")).copy()
        d["p10"] = num(d, "p10")
        d["p90"] = num(d, "p90")
        d["spread"] = d["p90"] - d["p10"]
        d = d.dropna(subset=["spread"]).sort_values("spread", ascending=False)
        fig, ax = new_fig(9.2, 5.2)
        labels = _clean_labels(d, "sector")
        hbar(ax, labels, d["spread"].to_numpy(), value_fmt=pct_fmt)
        style(ax, "How wide is the margin spread inside each sector?",
              "Distance between the 10th and 90th percentile net margin",
              SOURCE_FORBES)
        save(fig, book.out_dir / _target(book), SOURCE_FORBES)

    book.add("margin_dispersion", "How wide is the margin spread inside each sector?",
             "10th to 90th percentile net margin", SOURCE_FORBES, dispersion)

    def roa_decomp():
        d = frame(t.get("sectors")).copy()
        d["margin"] = num(d, "profit_margin") * 100
        d["turn"] = num(d, "asset_turnover")
        d["kind"] = col(d, "kind", default=None)
        if d["kind"] is None or d["kind"].isna().all():
            # The ``sectors`` table has no ``kind`` column, so classify the
            # sectors ourselves: ROA is exactly margin x turnover, and the
            # quadrant a sector sits in says which factor carries the result.
            med_m = d["margin"].median()
            med_t = d["turn"].median()
            d["kind"] = np.where(
                (d["margin"] >= med_m) & (d["turn"] >= med_t), "margin-driven",
                np.where((d["margin"] < med_m) & (d["turn"] >= med_t),
                         "turnover-driven", "compressed"))
        d = d.dropna(subset=["margin", "turn"])
        fig, ax = new_fig(9.2, 5.6)
        for kind, colr, marker in (("margin-driven", PALETTE[6], "o"),
                                   ("turnover-driven", PALETTE[1], "s"),
                                   ("compressed", PALETTE[13], "^")):
            sub = d[d["kind"] == kind]
            if sub.empty:
                continue
            ax.scatter(sub["turn"], sub["margin"], s=58, color=colr, alpha=0.85,
                       edgecolors="white", linewidths=0.8, zorder=3,
                       label=kind.replace("-", " "))
        for _, r in d.iterrows():
            ax.annotate(str(r.get("sector", "")),
                        (float(r["turn"]), float(r["margin"])), fontsize=8,
                        color="#4A5563", xytext=(4, 4),
                        textcoords="offset points")
        ax.set_xscale("log")
        ax.set_xlabel("Asset turnover (revenue ÷ assets, log scale)")
        ax.set_ylabel("Net margin (%)")
        if ax.get_legend_handles_labels()[0]:
            ax.legend(fontsize=9)
        style(ax, "Every sector is margin-driven or turnover-driven",
              "Return on assets is exactly margin × turnover, so the two "
              "multiplicands tell the story", SOURCE_FORBES)
        save(fig, book.out_dir / _target(book), SOURCE_FORBES)

    book.add("roa_decomposition", "Every sector is margin-driven or turnover-driven",
             "Net margin against asset turnover", SOURCE_FORBES, roa_decomp)

    def conc():
        d = frame(t.get("sector_concentration")).copy()
        share = num(d, "hhi", "concentration", "hhi_points", "top_share")
        if share.empty:
            label = col(d, "sector", "industry", default=None)
            if label is None:
                return
            share = pd.Series(np.arange(len(d), 0, -1), index=d.index)
        d = d.assign(_v=share)
        d = d.dropna(subset=["_v"]).sort_values("_v", ascending=False)
        fig, ax = new_fig(9.2, 5.0)
        labels = _clean_labels(d, "sector", "industry")
        hbar(ax, labels, d["_v"].to_numpy(),
             value_fmt=lambda v: f"{v:,.0f}")
        style(ax, "Concentration inside each sector",
              "Herfindahl index on revenue — how few firms dominate each "
              "industry", SOURCE_FORBES)
        save(fig, book.out_dir / _target(book), SOURCE_FORBES)

    book.add("sector_concentration", "Concentration inside each sector",
             "Herfindahl index on revenue", SOURCE_FORBES, conc)


# --------------------------------------------------------------------------- #
# ownership
# --------------------------------------------------------------------------- #
def charts_ownership(book: ChartBook, ctx, res) -> None:
    t = res["tables"]

    def ownership_mix():
        d = frame(t.get("ownership_mixed")).copy()
        d["rev"] = num(d, "revenue_usd")
        d = d.dropna(subset=["rev"]).sort_values("rev", ascending=False)
        fig, ax = new_fig(9.2, 4.8)
        labels = _clean_labels(d, "ownership")
        hbar(ax, labels, _fmt_billions(d["rev"]))
        style(ax, "Who owns the world's corporate revenue?",
              "By ownership type, across the reconciled universe", SOURCE_MIXED)
        save(fig, book.out_dir / _target(book), SOURCE_MIXED)

    book.add("ownership_mix", "Who owns the world's corporate revenue?",
             "Revenue by ownership type", SOURCE_MIXED, ownership_mix)

    def invisible():
        d = frame(t.get("invisible_giants")).copy()
        d["rev"] = num(d, "revenue_usd", "revenue_musd")
        if d["rev"].max() and d["rev"].max() > 1e6:
            d["rev"] = d["rev"] / 1e9
        d = d.dropna(subset=["rev"]).nlargest(25, "rev")
        fig, ax = new_fig(9.2, 7.0)
        labels = _clean_labels(d, "company")
        hbar(ax, labels, d["rev"].to_numpy())
        style(ax, "The invisible giants",
              "Companies with measured revenue that Forbes' Global 2000 never "
              "lists", SOURCE_MIXED)
        save(fig, book.out_dir / _target(book), SOURCE_MIXED)

    book.add("invisible_giants", "The invisible giants",
             "Measured companies missing from the Global 2000", SOURCE_MIXED,
             invisible)

    def true_top():
        d = frame(t.get("true_top100")).copy()
        d["rev"] = num(d, "revenue_usd", "revenue_musd")
        if len(d) and d["rev"].max() and d["rev"].max() > 1e6:
            d["rev"] = d["rev"] / 1e9
        fig, ax = new_fig(9.2, 7.2)
        labels = _clean_labels(d, "company")
        hbar(ax, labels, d["rev"].to_numpy(),
             highlight=labels.iloc[0] if len(labels) else None)
        style(ax, "The true top 100 on earth",
              "Re-ranked from the reconciled universe, not from the Forbes list",
              SOURCE_MIXED)
        save(fig, book.out_dir / _target(book), SOURCE_MIXED)

    book.add("true_top100", "The true top 100 on earth",
             "Re-ranked from the reconciled universe", SOURCE_MIXED, true_top)

    def margin_by_owner():
        d = frame(t.get("margin_tests")).copy()
        med = num(d, "median_b", "median_b_margin", "median")
        a = _clean_labels(d, "group_a", "label_a", "comparison", default="")
        b = _clean_labels(d, "group_b", "label_b", default="")
        if med.empty or not len(d):
            return
        fig, ax = new_fig(9.2, 5.2)
        labels = []
        vals = []
        for _, r in d.iterrows():
            lbl = f"{a.iloc[len(labels)]} vs {b.iloc[len(labels)]}" \
                if len(labels) < len(a) else "comparison"
            labels.append(lbl)
            vals.append(float(r["median_b"]) if "median_b" in d.columns
                        else float(med.iloc[len(vals)]))
        hbar(ax, labels, vals, value_fmt=pct_fmt)
        style(ax, "Median net margin, owner by owner",
              "State, listed, private and mutual businesses compared",
              SOURCE_MIXED)
        save(fig, book.out_dir / _target(book), SOURCE_MIXED)

    book.add("margin_by_ownership", "Median net margin, owner by owner",
             "State, listed, private and mutual businesses", SOURCE_MIXED,
             margin_by_owner)


# --------------------------------------------------------------------------- #
# capital
# --------------------------------------------------------------------------- #
def charts_capital(book: ChartBook, ctx, res) -> None:
    t = res["tables"]

    def top_listed():
        d = frame(t.get("top_listed")).copy()
        d["mc"] = num(d, "market_cap_usd")
        d = d.dropna(subset=["mc"]).nlargest(20, "mc")
        fig, ax = new_fig(9.2, 6.4)
        labels = _clean_labels(d, "company")
        hbar(ax, labels, _fmt_billions(d["mc"]),
             highlight=labels.iloc[0] if len(labels) else None)
        style(ax, "The twenty most valuable listed companies",
              "Market capitalisation, measured universe", SOURCE_MIXED)
        save(fig, book.out_dir / _target(book), SOURCE_MIXED)

    book.add("top_listed", "The twenty most valuable listed companies",
             "Market capitalisation", SOURCE_MIXED, top_listed)

    def multiples():
        d = frame(t.get("multiples_by_sector")).copy()
        # The capital module stores the sector price-to-sales as ``median_ps``
        # (with ``p25_ps``/``p75_ps`` around it), so look for that name first.
        m = num(d, "median_ps", "market_cap_to_revenue", "ps", "ev_sales",
                "multiple")
        if m.empty:
            m = num(d, "market_cap_to_profit", "pe")
        if m.empty:
            return
        d = d.assign(_m=m).dropna(subset=["_m"]).sort_values("_m", ascending=False)
        fig, ax = new_fig(9.2, 5.0)
        labels = _clean_labels(d, "sector")
        hbar(ax, labels, d["_m"].to_numpy(),
             value_fmt=lambda v: f"{v:,.1f}x")
        style(ax, "What the market pays for each unit of revenue",
              "Market capitalisation ÷ revenue, by sector", SOURCE_MIXED)
        save(fig, book.out_dir / _target(book), SOURCE_MIXED)

    book.add("multiples_by_sector", "What the market pays for each unit of revenue",
             "Market capitalisation ÷ revenue, by sector", SOURCE_MIXED,
             multiples)

    def profit_vs_mcap():
        d = frame(t.get("profit_pool")).copy()
        gap = num(d, "profit_minus_mcap_pp")
        if gap.empty:
            return
        d = d.dropna(subset=["profit_minus_mcap_pp"]).sort_values(
            "profit_minus_mcap_pp", ascending=False)
        fig, ax = new_fig(9.2, 5.0)
        labels = _clean_labels(d, "sector")
        diverging_hbar(ax, labels, gap.to_numpy(),
                       value_fmt=lambda v: f"{v:+.1f} pp")
        style(ax, "Profit and market value disagree about what matters",
              "Percentage points of profit share minus percentage points of "
              "market-value share", SOURCE_MIXED)
        save(fig, book.out_dir / _target(book), SOURCE_MIXED)

    book.add("profit_vs_mcap", "Profit and market value disagree about what matters",
             "Profit share minus market-value share, by sector", SOURCE_MIXED,
             profit_vs_mcap)

    def depth():
        d = frame(t.get("financial_depth")).copy()
        ratio = num(d, "mcap_to_gdp")
        gdp = num(d, "gdp")
        if not gdp.empty:
            d = d[(gdp >= 1e11) & (num(d, "companies") >= 5)]
        d = d.dropna(subset=["mcap_to_gdp"]).sort_values(
            "mcap_to_gdp", ascending=False).head(20)
        if d.empty:
            return
        fig, ax = new_fig(9.2, 5.4)
        labels = _clean_labels(d, "country")
        hbar(ax, labels, d["mcap_to_gdp"].to_numpy(),
             value_fmt=lambda v: f"{v:,.1f}x")
        style(ax, "How deep is each equity market?",
              "Market capitalisation as a multiple of GDP, for economies with "
              "at least $100B of output and five listed companies", SOURCE_MIXED)
        save(fig, book.out_dir / _target(book), SOURCE_MIXED)

    book.add("financial_depth", "How deep is each equity market?",
             "Market capitalisation as a multiple of GDP", SOURCE_MIXED, depth)

    def exchanges():
        d = frame(t.get("exchanges")).copy()
        mc = num(d, "total_market_cap_usd", "market_cap_usd")
        if mc.empty:
            return
        d = d.assign(_m=mc).dropna(subset=["_m"]).nlargest(20, "_m")
        fig, ax = new_fig(9.2, 5.6)
        labels = _clean_labels(d, "exchange", "name")
        hbar(ax, labels, _fmt_billions(d["_m"]))
        style(ax, "The world's exchanges by market value",
              "Aggregate market capitalisation of listed companies per venue",
              SOURCE_MIXED)
        save(fig, book.out_dir / _target(book), SOURCE_MIXED)

    book.add("exchanges", "The world's exchanges by market value",
             "Aggregate market capitalisation per venue", SOURCE_MIXED,
             exchanges)


# --------------------------------------------------------------------------- #
# private capital
# --------------------------------------------------------------------------- #
def charts_private(book: ChartBook, ctx, res) -> None:
    t = res["tables"]
    m = res["metrics"]

    def uni_country():
        d = frame(t.get("unicorns_by_country")).copy()
        v = num(d, "valuation_usd")
        if v.empty:
            return
        d = d.assign(_v=v).dropna(subset=["_v"]).nlargest(20, "_v")
        fig, ax = new_fig(9.2, 5.4)
        labels = _clean_labels(d, "country")
        hbar(ax, labels, _fmt_billions(d["_v"]))
        style(ax, "Where the private giants are",
              "Paper valuation of unicorn companies by country", SOURCE_MIXED)
        save(fig, book.out_dir / _target(book), SOURCE_MIXED)

    book.add("unicorns_country", "Where the private giants are",
             "Unicorn paper valuation by country", SOURCE_MIXED, uni_country)

    def uni_industry():
        d = frame(t.get("unicorns_by_industry")).copy()
        v = num(d, "valuation_usd")
        if v.empty:
            return
        d = d.assign(_v=v).dropna(subset=["_v"]).nlargest(20, "_v")
        fig, ax = new_fig(9.2, 5.4)
        labels = _clean_labels(d, "industry")
        hbar(ax, labels, _fmt_billions(d["_v"]))
        style(ax, "Which industries the private money went into",
              "Paper valuation of unicorn companies by industry", SOURCE_MIXED)
        save(fig, book.out_dir / _target(book), SOURCE_MIXED)

    book.add("unicorns_industry", "Which industries the private money went into",
             "Unicorn paper valuation by industry", SOURCE_MIXED, uni_industry)

    def uni_years():
        rows = (m.get("unicorns", {}) or {}).get("by_year_joined", [])
        d = frame(rows)
        if d.empty:
            return
        d["year"] = num(d, "year")
        d["n"] = num(d, "companies")
        d = d.dropna(subset=["year"]).sort_values("year")
        fig, ax = new_fig(9.2, 4.6)
        ax.bar(d["year"], d["n"], color=PALETTE[1], width=0.75, zorder=3)
        ax.set_ylabel("Companies crossing $1B")
        ax.set_xlabel("Year")
        style(ax, "The unicorn wave",
              "How many companies crossed the $1B mark each year",
              "Source: CB Insights unicorn list, as loaded by the analysis engine.")
        save(fig, book.out_dir / _target(book),
             "Source: CB Insights unicorn list.")

    book.add("unicorn_wave", "The unicorn wave",
             "Companies crossing $1B each year",
             "Source: CB Insights unicorn list.", uni_years)

    def unlisted():
        d = frame(t.get("unlisted_top")).copy()
        r = num(d, "revenue_usd", "revenue_musd")
        if r.empty:
            return
        d = d.assign(_r=r).dropna(subset=["_r"]).nlargest(25, "_r")
        if d["_r"].max() > 1e6:
            d["_r"] = d["_r"] / 1e9
        fig, ax = new_fig(9.2, 7.0)
        labels = _clean_labels(d, "company")
        hbar(ax, labels, d["_r"].to_numpy())
        style(ax, "Real revenue with no listed share",
              "Companies with measured revenue and no public equity",
              SOURCE_MIXED)
        save(fig, book.out_dir / _target(book), SOURCE_MIXED)

    book.add("unlisted_top", "Real revenue with no listed share",
             "Measured revenue, no public equity", SOURCE_MIXED, unlisted)

    def ai_modality():
        d = frame(t.get("ai_by_modality")).copy()
        n = num(d, "companies")
        if n.empty:
            return
        d = d.dropna(subset=["companies"]).sort_values("companies", ascending=False)
        fig, ax = new_fig(9.2, 5.0)
        labels = _clean_labels(d, "modality")
        hbar(ax, labels, d["companies"].to_numpy(), value_fmt=count_fmt)
        style(ax, "The AI builders by modality",
              "173 companies that build machine-learning models, grouped by "
              "what they build", "Source: AI company list in the analysis engine.")
        save(fig, book.out_dir / _target(book),
             "Source: AI company list.")

    book.add("ai_modality", "The AI builders by modality",
             "Model builders grouped by what they build",
             "Source: AI company list in the analysis engine.", ai_modality)


# --------------------------------------------------------------------------- #
# time series
# --------------------------------------------------------------------------- #
def charts_time(book: ChartBook, ctx, res) -> None:
    t = res["tables"]
    m = res["metrics"]

    def cohort_revenue():
        d = frame(t.get("cohort_revenue_series")).copy()
        if d.empty:
            return
        d["year"] = num(d, "year")
        d["total"] = num(d, "total")
        d = d.dropna(subset=["year", "total"]).sort_values("year")
        fig, ax = new_fig(9.2, 4.8)
        ax.plot(d["year"], d["total"] / 1000.0, color=BAR, lw=2.2, marker="o",
                ms=4, zorder=3)
        ax.set_ylabel("Cohort revenue, USD trillions")
        ax.set_xlabel("Year")
        cr = m.get("cohort_revenue", {}) or {}
        sub = (f"{cr.get('companies', 0):,} companies · "
               f"CAGR {cr.get('cagr_pct', float('nan')):.2f}% over "
               f"{cr.get('span_years', 0)} years")
        style(ax, "The constant cohort", sub,
              "Source: Forbes Global 2000 historical dataset, constant "
              "membership panel.")
        save(fig, book.out_dir / _target(book),
             "Source: Forbes Global 2000 history.")

    book.add("cohort_revenue", "The constant cohort",
             "Revenue of a fixed set of companies over time",
             "Source: Forbes Global 2000 history.", cohort_revenue)

    def cohort_margin():
        d = frame(t.get("cohort_margin_path")).copy()
        if d.empty:
            return
        d["year"] = num(d, "year")
        d["margin"] = num(d, "margin_pct")
        d = d.dropna(subset=["year", "margin"]).sort_values("year")
        fig, ax = new_fig(9.2, 4.6)
        ax.plot(d["year"], d["margin"], color=ACCENT, lw=2.2, marker="o", ms=4,
                zorder=3)
        ax.set_ylabel("Cohort net margin (%)")
        ax.set_xlabel("Year")
        style(ax, "Did the cohort get more profitable?",
              "Net margin of the same fixed set of companies, year by year",
              "Source: Forbes Global 2000 history.")
        save(fig, book.out_dir / _target(book),
             "Source: Forbes Global 2000 history.")

    book.add("cohort_margin", "Did the cohort get more profitable?",
             "Net margin of a fixed cohort", "Source: Forbes Global 2000 history.",
             cohort_margin)

    def mobility():
        d = frame(t.get("rank_mobility")).copy()
        g = num(d, "growth_pct")
        if g.empty:
            return
        d = d.assign(_g=g).dropna(subset=["_g"])
        top = d.nlargest(15, "_g")
        bot = d.nsmallest(15, "_g")
        sub = pd.concat([top, bot])
        sub = sub.sort_values("_g", ascending=False)
        fig, ax = new_fig(9.2, 7.0)
        labels = _clean_labels(sub, "company")
        diverging_hbar(ax, labels, sub["_g"].to_numpy(),
                       value_fmt=lambda v: f"{v:,.0f}%")
        style(ax, "Who grew, who shrank",
              "Revenue change over the historical window for the same "
              "companies", "Source: Forbes Global 2000 history.")
        save(fig, book.out_dir / _target(book),
             "Source: Forbes Global 2000 history.")

    book.add("rank_mobility", "Who grew, who shrank",
             "Revenue change for the same companies over time",
             "Source: Forbes Global 2000 history.", mobility)

    def pool_migration():
        d = frame(t.get("profit_pool_migration")).copy()
        g = num(d, "profit_share_change_pp")
        if g.empty:
            return
        d = d.dropna(subset=["profit_share_change_pp"]).sort_values(
            "profit_share_change_pp", ascending=False)
        fig, ax = new_fig(9.2, 5.4)
        labels = _clean_labels(d, "industry")
        diverging_hbar(ax, labels, d["profit_share_change_pp"].to_numpy(),
                       value_fmt=lambda v: f"{v:+.1f} pp")
        style(ax, "Where the profit pool moved",
              "Change in each industry's share of the cohort's total profit",
              "Source: Forbes Global 2000 history.")
        save(fig, book.out_dir / _target(book),
             "Source: Forbes Global 2000 history.")

    book.add("profit_pool_migration", "Where the profit pool moved",
             "Change in industry share of total profit",
             "Source: Forbes Global 2000 history.", pool_migration)


# --------------------------------------------------------------------------- #
# data quality
# --------------------------------------------------------------------------- #
def charts_quality(book: ChartBook, ctx, res) -> None:
    t = res["tables"]

    def missing():
        d = frame(t.get("missingness_key")).copy()
        p = num(d, "missing_pct")
        if p.empty:
            return
        d = d.dropna(subset=["missing_pct"]).sort_values("missing_pct",
                                                         ascending=False)
        d = d.head(20)
        fig, ax = new_fig(9.2, 6.4)
        labels = [f"{a} · {b}" for a, b in zip(
            _clean_labels(d, "dataset"), _clean_labels(d, "column"))]
        hbar(ax, labels, d["missing_pct"].to_numpy(),
             value_fmt=lambda v: f"{v:,.0f}%")
        style(ax, "Where the data is thin",
              "Share of empty cells in the fields that matter most",
              "Source: completeness audit across all 22 datasets.")
        save(fig, book.out_dir / _target(book),
             "Source: completeness audit.")

    book.add("missingness", "Where the data is thin",
             "Share of empty cells in key fields",
             "Source: completeness audit.", missing)

    def confidence():
        d = frame(t.get("confidence")).copy()
        # The data-quality module names the per-company score
        # ``confidence_score``.
        c = num(d, "confidence_score", "confidence")
        if c.empty:
            return
        c = c.dropna()
        fig, ax = new_fig(9.2, 4.6)
        ax.hist(c, bins=40, color=PALETTE[1], edgecolor="white", zorder=3)
        ax.set_xlabel("Confidence score")
        ax.set_ylabel("Companies")
        style(ax, "How much to trust each row",
              "Every company carries a score built from source trust, "
              "corroboration and completeness", "Source: analysis engine.")
        save(fig, book.out_dir / _target(book), "Source: analysis engine.")

    book.add("confidence", "How much to trust each row",
             "Distribution of the confidence score", "Source: analysis engine.",
             confidence)

    def disagreement():
        d = frame(t.get("cross_source_disagreement")).copy()
        # The audit table names the headline number ``median_abs_pct_diff``.
        med = num(d, "median_abs_pct_diff", "median_rel_diff_pct",
                  "median_diff_pct", "median_abs_diff_pct")
        if med.empty:
            med = num(d, "median")
        if med.empty:
            return
        d = d.assign(_m=med).dropna(subset=["_m"]).sort_values("_m",
                                                                ascending=False)
        fig, ax = new_fig(9.2, 4.8)
        labels = [f"{a} vs {b}" for a, b in zip(
            _clean_labels(d, "source_a"), _clean_labels(d, "source_b"))]
        hbar(ax, labels, d["_m"].to_numpy(),
             value_fmt=lambda v: f"{v:,.1f}%")
        style(ax, "Do the sources agree?",
              "Median relative difference in revenue between source pairs",
              "Source: cross-source audit.")
        save(fig, book.out_dir / _target(book), "Source: cross-source audit.")

    book.add("cross_source", "Do the sources agree?",
             "Median revenue disagreement between source pairs",
             "Source: cross-source audit.", disagreement)


# --------------------------------------------------------------------------- #
# companies
# --------------------------------------------------------------------------- #
def charts_companies(book: ChartBook, ctx, res) -> None:
    """One dot per company -- the whole population, not a top slice."""
    t = res["tables"]
    presence = frame(t.get("company_presence")).copy()
    if presence.empty:
        return

    def dot_plot(value_col: str, title: str, subtitle: str, source: str,
                 ylabel: str, caption: str):
        def draw():
            d = presence.copy()
            v = num(d, value_col)
            if v.empty:
                return
            d = d.assign(_v=v).dropna(subset=["_v", "rank_by_revenue"])
            d = d[d["_v"] > 0]
            if d.empty:
                return
            sectors = d["sector"].fillna("Unknown").astype(str)
            top = list(sectors.value_counts().head(8).index)
            colours = [PALETTE[i % len(PALETTE)] if s in top else "#C3CBD6"
                       for i, s in enumerate(sectors)]
            fig, ax = new_fig(9.4, 5.6)
            ax.scatter(d["rank_by_revenue"], d["_v"] / 1e9, s=8, c=colours,
                       alpha=0.45, linewidths=0, zorder=3)
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_xlabel("Company rank (log scale)")
            ax.set_ylabel(ylabel)
            handles = [Line2D([], [], marker="o", linestyle="none", markersize=6,
                              color=PALETTE[i % len(PALETTE)], label=name)
                       for i, name in enumerate(top)]
            if handles:
                ax.legend(handles=handles, fontsize=8, loc="upper right",
                          ncol=2, frameon=False)
            style(ax, title, subtitle, source)
            save(fig, book.out_dir / _target(book), source)

        book.add(title_slug(title), title, subtitle, source, draw, caption)

    dot_plot(
        "revenue_usd",
        "Every company we can measure",
        "One dot per company, ranked by revenue",
        "Source: reconciled universe of all measured companies.",
        "Revenue (US$ billions, log scale)",
        "Every company with a revenue figure, plotted on a log-log grid. "
        "The head is a handful of giants; the tail is tens of thousands of "
        "firms each too small to see in a ranked list.")
    dot_plot(
        "market_cap_usd",
        "Every company the market can see",
        "One dot per company with a market value",
        "Source: reconciled universe of all measured companies.",
        "Market value (US$ billions, log scale)",
        "The listed universe only: companies with a quoted price. The gap "
        "between the top of this cloud and the top of the revenue chart is "
        "the part of the corporate world that has no ticker.")


def title_slug(title: str) -> str:
    """Filesystem-friendly slug for a chart title."""
    keep = [c.lower() if c.isalnum() else "_" for c in title]
    slug = "".join(keep)
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_")


# --------------------------------------------------------------------------- #
# target helper
# --------------------------------------------------------------------------- #
def _target(book: ChartBook) -> str:
    """The file name the chart currently being drawn should be written to."""
    return book._pending


__all__ = ["ChartBook", "charts_scale", "charts_geography", "charts_industry",
           "charts_ownership", "charts_capital", "charts_private",
           "charts_time", "charts_quality", "charts_companies",
           "col", "num", "frame"]
