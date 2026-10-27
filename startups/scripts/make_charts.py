"""Charts for the global startup dataset."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "charts"
OUT.mkdir(parents=True, exist_ok=True)
df = pd.read_csv(BASE / "data" / "startups_global.csv")

INK, BAR, ACCENT, MUTED, BG = "#0B2545", "#1B6CA8", "#E07A4F", "#9AA5B1", "#FFFFFF"
plt.rcParams.update({
    "font.family": "Segoe UI", "figure.facecolor": BG, "axes.facecolor": BG,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK, "ytick.color": INK, "figure.dpi": 200, "savefig.dpi": 200,
})


def top20() -> None:
    d = df.nlargest(20, "valuation_busd").sort_values("valuation_busd")
    fig, ax = plt.subplots(figsize=(9, 6.2))
    y = np.arange(len(d))
    ax.barh(y, d.valuation_busd, color=BAR, height=0.65)
    ax.barh(y[-2:], d.valuation_busd.values[-2:], color=ACCENT, height=0.65)
    ax.set_yticks(y)
    ax.set_yticklabels(d.company, fontsize=9)
    for yi, v in zip(y, d.valuation_busd):
        ax.text(v + d.valuation_busd.max() * 0.012, yi, f"${v:,.0f}B", va="center", fontsize=8.5)
    ax.set_xlim(0, d.valuation_busd.max() * 1.18)
    ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}B"))
    ax.grid(axis="x", color="#E4E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_title("The most valuable private companies on earth", loc="left",
                 fontsize=15, fontweight="bold", pad=18)
    ax.text(0, 1.02, "Valuation as reported by CB Insights Unicorn Board",
            transform=ax.transAxes, fontsize=10, color="#4A5568")
    fig.text(0, -0.02, "Source: CB Insights (public unicorn board). Private marks, not "
                       "tradable prices.", fontsize=7.5, color=MUTED)
    fig.savefig(OUT / "st01_top_unicorns.png", bbox_inches="tight")
    plt.close(fig)


def countries() -> None:
    g = (df.dropna(subset=["country"])
           .groupby("country")
           .agg(n=("company", "count"), val=("valuation_busd", "sum"))
           .nlargest(15, "n").sort_values("n"))
    fig, ax = plt.subplots(figsize=(9, 5.6))
    y = np.arange(len(g))
    ax.barh(y, g.n, color=BAR, height=0.65)
    ax.set_yticks(y)
    ax.set_yticklabels(g.index, fontsize=9)
    for yi, (n, v) in zip(y, zip(g.n, g.val)):
        ax.text(n + 4, yi, f"{n}  (${v:,.0f}B)", va="center", fontsize=8.5)
    ax.set_xlim(0, g.n.max() * 1.25)
    ax.set_xlabel("Number of unicorns", fontsize=9)
    ax.grid(axis="x", color="#E4E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_title("Where the unicorns are", loc="left", fontsize=15, fontweight="bold", pad=18)
    ax.text(0, 1.02, "Unicorns by headquarters country, with combined valuation",
            transform=ax.transAxes, fontsize=10, color="#4A5568")
    fig.text(0, -0.02, "Source: CB Insights. Counts are companies, not dollars.",
             fontsize=7.5, color=MUTED)
    fig.savefig(OUT / "st02_countries.png", bbox_inches="tight")
    plt.close(fig)


def industries() -> None:
    g = (df.dropna(subset=["industry"])
           .groupby("industry")
           .agg(n=("company", "count"), val=("valuation_busd", "sum"))
           .sort_values("val", ascending=False).head(10).sort_values("val"))
    fig, ax = plt.subplots(figsize=(9, 5.2))
    y = np.arange(len(g))
    ax.barh(y, g.val, color=BAR, height=0.65)
    ax.set_yticks(y)
    ax.set_yticklabels(g.index, fontsize=9)
    for yi, (v, n) in zip(y, zip(g.val, g.n)):
        ax.text(v + g.val.max() * 0.01, yi, f"${v:,.0f}B  ({n})", va="center", fontsize=8.5)
    ax.set_xlim(0, g.val.max() * 1.2)
    ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}B"))
    ax.grid(axis="x", color="#E4E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_title("What the unicorns do", loc="left", fontsize=15, fontweight="bold", pad=18)
    ax.text(0, 1.02, "Combined valuation by sector (company count in brackets)",
            transform=ax.transAxes, fontsize=10, color="#4A5568")
    fig.text(0, -0.02, "Source: CB Insights Unicorn Board", fontsize=7.5, color=MUTED)
    fig.savefig(OUT / "st03_industries.png", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    top20()
    countries()
    industries()
    print("wrote startup charts")
