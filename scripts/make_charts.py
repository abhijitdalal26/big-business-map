"""Publication-quality charts from the Global 2000 dataset.

Outputs PNGs in output/charts/ at 200 dpi, sized for a Substack post.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

DATA = Path("data/global2000_2025.csv")
OUT = Path("output/charts")
OUT.mkdir(parents=True, exist_ok=True)

INK = "#0B2545"      # near-black navy for text
BAR = "#1B6CA8"      # primary bar
ACCENT = "#E07A4F"   # highlight
MUTED = "#9AA5B1"    # secondary
BG = "#FFFFFF"

plt.rcParams.update({
    "font.family": "Segoe UI",
    "figure.facecolor": BG,
    "axes.facecolor": BG,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 200,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
})


def style(ax, title, subtitle, source="Source: Forbes Global 2000 (2025)"):
    ax.set_title(title, loc="left", fontsize=15, fontweight="bold", color=INK, pad=18)
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=10, color="#4A5568",
            va="bottom", ha="left")
    ax.figure.text(0, -0.02, source, fontsize=8, color=MUTED, ha="left")


def _trim(x: float) -> str:
    s = f"{x:,.1f}"
    return s.rstrip("0").rstrip(".")


def money_b(v: float) -> str:
    """Format a USD-billions value: 0 -> $0, 0.1 -> $100M, 681 -> $681B, 6368 -> $6.4T."""
    if v == 0:
        return "$0"
    if abs(v) >= 1000:
        return f"${_trim(v / 1000)}T"
    if abs(v) >= 1:
        return f"${_trim(v)}B"
    return f"${_trim(v * 1000)}M"


def money_axis(x, _):
    """Axis tick for values expressed in USD billions."""
    return money_b(x)


def money_axis_m(x, _):
    """Axis tick for values expressed in USD millions."""
    return money_b(x / 1000)


def hbar(ax, labels, values, fmt, highlight_idx=None):
    y = np.arange(len(labels))[::-1]
    colors = [ACCENT if (highlight_idx is not None and i == highlight_idx) else BAR
              for i in range(len(labels))]
    ax.barh(y, values, color=colors, height=0.68)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.grid(axis="x", color="#E4E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    vmax = max(values)
    for yi, v in zip(y, values):
        ax.text(v + vmax * 0.012, yi, fmt(v), va="center", fontsize=8.5, color=INK)
    ax.set_xlim(0, vmax * 1.16)


def main() -> None:
    df = pd.read_csv(DATA)

    # ---------- 1. Top 15 by revenue ----------
    d = df.nlargest(15, "revenue_musd").sort_values("revenue_musd", ascending=False)
    labels = [f"{c}" for c in d["company"]]
    values = (d["revenue_musd"] / 1000).tolist()
    fig, ax = plt.subplots(figsize=(9, 5.6))
    hbar(ax, labels, values, money_b)
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(money_axis))
    style(ax, "The revenue giants", "Top 15 companies by revenue, FY2024 (USD billions)")
    fig.savefig(OUT / "01_top_revenue.png")
    plt.close(fig)

    # ---------- 2. Top 15 by market value ----------
    d = df.nlargest(15, "market_value_musd")
    labels = [c for c in d["company"]]
    values = (d["market_value_musd"] / 1000).tolist()
    fig, ax = plt.subplots(figsize=(9, 5.6))
    hbar(ax, labels, values, money_b)
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(money_axis))
    style(ax, "The market-cap club", "Top 15 companies by market value, May 2025 (USD billions)")
    fig.savefig(OUT / "02_top_market_value.png")
    plt.close(fig)

    # ---------- 3. Companies by country ----------
    counts = df["country"].value_counts().head(15)
    labels = counts.index.tolist()
    values = counts.values.tolist()
    fig, ax = plt.subplots(figsize=(9, 5.6))
    hbar(ax, labels, values, lambda v: f"{v:,}", highlight_idx=0)
    ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
    style(ax, "Where the giants live",
          "Number of Global 2000 companies by headquarters country")
    fig.savefig(OUT / "03_country_count.png")
    plt.close(fig)

    # ---------- 4. Revenue by industry ----------
    ind = (df.groupby("industry", as_index=False)
             .agg(revenue=("revenue_musd", "sum"), profits=("profits_musd", "sum"),
                  n=("company", "count"))
             .nlargest(14, "revenue"))
    labels = ind["industry"].tolist()
    values = (ind["revenue"] / 1000).tolist()
    fig, ax = plt.subplots(figsize=(9, 5.8))
    hbar(ax, labels, values, money_b)
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(money_axis))
    style(ax, "Which industries move the most money",
          "Combined revenue of Global 2000 companies by industry, FY2024")
    fig.savefig(OUT / "04_industry_revenue.png")
    plt.close(fig)

    # ---------- 5. Revenue vs market value scatter ----------
    fig, ax = plt.subplots(figsize=(9, 6.2))
    regions = df["region"].fillna("Other").unique().tolist()
    palette = {"North America": "#1B6CA8", "Asia-Pacific": "#E07A4F",
               "Europe": "#5C9E6E", "Middle East & Central Asia": "#B084CC",
               "Latin America": "#E9C46A", "Africa": "#8D6E63"}
    for r in regions:
        sub = df[df["region"] == r]
        ax.scatter(sub["revenue_musd"], sub["market_value_musd"],
                   s=18, alpha=0.65, label=r, color=palette.get(r, MUTED),
                   edgecolors="none")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(money_axis_m))
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(money_axis_m))
    ax.grid(color="#E4E7EB", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.set_xlabel("Revenue (log scale)", fontsize=10)
    ax.set_ylabel("Market value (log scale)", fontsize=10)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    labels = {
        "Apple": ("Apple", -8, 0, "right"),
        "NVIDIA": ("NVIDIA", -8, 10, "right"),
        "Saudi Arabian Oil Company (Saudi Aramco)": ("Saudi Aramco", -8, 8, "right"),
        "Walmart": ("Walmart", -8, -10, "right"),
    }
    for name, (display, dx, dy, ha) in labels.items():
        row = df[df["company"] == name]
        if row.empty:
            continue
        ax.annotate(display, (row["revenue_musd"].iloc[0], row["market_value_musd"].iloc[0]),
                    fontsize=9, color=INK, xytext=(dx, dy), textcoords="offset points",
                    ha=ha, va="center")
    ax.set_xlim(right=df["revenue_musd"].max() * 1.15)
    ax.set_ylim(top=df["market_value_musd"].max() * 1.2)
    style(ax, "Revenue is not market value",
          "Each dot is one Global 2000 company; axes on log scales")
    fig.savefig(OUT / "05_revenue_vs_market_value.png")
    plt.close(fig)

    # ---------- 6. Median profit margin by industry ----------
    ind = df.dropna(subset=["profit_margin_pct"]).groupby("industry").agg(
        margin=("profit_margin_pct", "median"), n=("company", "count"))
    ind = ind[ind["n"] >= 15].nlargest(12, "margin")
    labels = ind.index.tolist()
    values = ind["margin"].tolist()
    fig, ax = plt.subplots(figsize=(9, 5.4))
    hbar(ax, labels, values, lambda v: f"{v:.1f}%")
    ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}%"))
    ax.xaxis.set_major_locator(mtick.MultipleLocator(5))
    style(ax, "The most profitable businesses",
          "Median net profit margin by industry (industries with 15+ companies)")
    fig.savefig(OUT / "06_industry_margin.png")
    plt.close(fig)

    # ---------- 7. Ten-year trend, constant cohort ----------
    hist = pd.read_csv("data/global2000_2025_history.csv")
    rev_h = hist[hist.metric == "revenue"]
    oldest = int(rev_h["years_ago"].max())
    cohort = set(rev_h.loc[rev_h["years_ago"] == oldest, "company"])
    sub = hist[hist["company"].isin(cohort)]

    def agg_metric(m: str) -> pd.Series:
        s = sub[sub.metric == m].groupby("years_ago")["value"].sum().sort_index()
        return s / s.iloc[-1] * 100  # index to 100 at the oldest year

    rev_idx = agg_metric("revenue")
    prof_idx = agg_metric("profits")
    years = [2024 - int(y) for y in rev_idx.index][::-1]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.plot(years, rev_idx.values[::-1], color=BAR, linewidth=2.4, marker="o", markersize=4,
            label="Revenue")
    ax.plot(years, prof_idx.values[::-1], color=ACCENT, linewidth=2.4, marker="o", markersize=4,
            label="Profit")
    ax.axhline(100, color=MUTED, linewidth=0.9, linestyle="--")
    ax.text(2015, 101.5, "2015 = 100", fontsize=8, color=MUTED)
    ax.grid(axis="y", color="#E4E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=10, loc="upper left")
    ax.set_ylabel("Index (2015 = 100)", fontsize=10)
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
    style(ax, "Big companies kept getting bigger",
          f"Revenue and profit of the {len(cohort):,} companies present in all ten editions")
    fig.savefig(OUT / "07_ten_year_trend.png")
    plt.close(fig)

    print("wrote charts to", OUT)


if __name__ == "__main__":
    main()
