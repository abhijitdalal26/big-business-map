"""Charts for the expanded listed universe (kept separate from the atlas charts)."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data" / "listed_universe.csv"
OUT = Path(__file__).resolve().parents[1] / "charts"
OUT.mkdir(parents=True, exist_ok=True)

INK, BAR, ACCENT, MUTED, BG = "#0B2545", "#1B6CA8", "#E07A4F", "#9AA5B1", "#FFFFFF"
plt.rcParams.update({
    "font.family": "Segoe UI", "figure.facecolor": BG, "axes.facecolor": BG,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK, "ytick.color": INK, "figure.dpi": 200, "savefig.dpi": 200,
})


def bands(df: pd.DataFrame) -> None:
    rev = df["revenue_usd"].dropna()
    edges = [(0, 1e9, "under $1B"), (1e9, 5e9, "$1–5B"), (5e9, 2e10, "$5–20B"),
             (2e10, 1e11, "$20–100B"), (1e11, np.inf, "over $100B")]
    labels, counts = [], []
    for lo, hi, label in edges:
        labels.append(label)
        counts.append(int(((rev >= lo) & (rev < hi)).sum()))

    fig, ax = plt.subplots(figsize=(9, 4.6))
    bars = ax.bar(labels, counts, color=[MUTED, BAR, BAR, BAR, ACCENT], width=0.62)
    for b, c in zip(bars, counts):
        ax.text(b.get_x() + b.get_width() / 2, c + max(counts) * 0.01, f"{c:,}",
                ha="center", fontsize=10, fontweight="bold")
    ax.set_ylim(0, max(counts) * 1.15)
    ax.grid(axis="y", color="#E4E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
    ax.set_title("How many companies are actually big", loc="left",
                 fontsize=15, fontweight="bold", pad=18)
    ax.text(0, 1.02, f"Companies with a revenue figure in the universe (n={len(rev):,})",
            transform=ax.transAxes, fontsize=10, color="#4A5568")
    fig.text(0, -0.04, "Sources: SEC XBRL (US, audited) and companiesmarketcap (non-US, estimate)",
             fontsize=8, color=MUTED)
    fig.savefig(OUT / "u01_revenue_bands.png", bbox_inches="tight")
    plt.close(fig)


def countries(df: pd.DataFrame) -> None:
    big = df[(df["revenue_usd"] > 1e9)].dropna(subset=["country"])
    counts = big["country"].value_counts().head(15)
    fig, ax = plt.subplots(figsize=(9, 5))
    y = np.arange(len(counts))[::-1]
    ax.barh(y, counts.values, color=BAR, height=0.65)
    ax.set_yticks(y)
    ax.set_yticklabels(counts.index, fontsize=9)
    for yi, v in zip(y, counts.values):
        ax.text(v + max(counts) * 0.01, yi, f"{v:,}", va="center", fontsize=9)
    ax.set_xlim(0, max(counts) * 1.12)
    ax.grid(axis="x", color="#E4E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_title("Where the data can see $1B+ companies", loc="left",
                 fontsize=15, fontweight="bold", pad=18)
    ax.text(0, 1.02, "Companies with revenue above $1B, by headquarters country",
            transform=ax.transAxes, fontsize=10, color="#4A5568")
    fig.text(0, -0.02, "Coverage bias, not reality: US figures are audited (SEC); non-US counts depend on "
                       "companiesmarketcap coverage (UK and China are undercounted).", fontsize=7.5, color=MUTED)
    fig.savefig(OUT / "u02_country_big.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    df = pd.read_csv(DATA)
    bands(df)
    countries(df)
    print("wrote universe charts")


if __name__ == "__main__":
    main()
