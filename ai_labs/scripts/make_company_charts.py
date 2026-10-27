"""Charts for the wide AI-companies dataset (all modalities)."""

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
df = pd.read_csv(BASE / "data" / "ai_companies.csv")

INK, OPEN, PARTIAL, CLOSED, ACCENT, MUTED, BG = "#0B2545", "#5C9E6E", "#E9C46A", "#9AA5B1", "#E07A4F", "#9AA5B1", "#FFFFFF"
plt.rcParams.update({
    "font.family": "Segoe UI", "figure.facecolor": BG, "axes.facecolor": BG,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK, "ytick.color": INK, "figure.dpi": 200, "savefig.dpi": 200,
})


def modalities() -> None:
    d = df.copy()
    d["mod"] = d["modality"].str.split(" / ").str[0]
    piv = d.pivot_table(index="mod", columns="open_weights", values="company",
                        aggfunc="count", fill_value=0)
    piv["total"] = piv.sum(axis=1)
    piv = piv.nlargest(12, "total").sort_values("total")
    fig, ax = plt.subplots(figsize=(9, 5.8))
    left = np.zeros(len(piv))
    for c, color, label in [("yes", OPEN, "Open weights"), ("partial", PARTIAL, "Partial"),
                            ("no", CLOSED, "Closed")]:
        vals = piv.get(c, pd.Series(0, index=piv.index)).values
        ax.barh(piv.index, vals, left=left, color=color, label=label, height=0.65)
        left += vals
    for i, total in enumerate(piv["total"].values):
        ax.text(total + 0.5, i, str(int(total)), va="center", fontsize=9)
    ax.set_xlim(0, piv["total"].max() * 1.15)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.grid(axis="x", color="#E4E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_title("The AI industry is not just chatbots", loc="left",
                 fontsize=15, fontweight="bold", pad=18)
    ax.text(0, 1.02, "Companies training models, by primary modality and openness",
            transform=ax.transAxes, fontsize=10, color="#4A5568")
    fig.text(0, -0.02, "Curated map of 173 model-builders; not an exhaustive census.",
             fontsize=7.5, color=MUTED)
    fig.savefig(OUT / "ai03_modalities.png", bbox_inches="tight")
    plt.close(fig)


def valuations() -> None:
    d = df.dropna(subset=["valuation_busd_cb"]).nlargest(15, "valuation_busd_cb")
    d = d.sort_values("valuation_busd_cb")
    fig, ax = plt.subplots(figsize=(9, 5.4))
    y = np.arange(len(d))
    ax.barh(y, d.valuation_busd_cb, color=ACCENT, height=0.65)
    ax.set_yticks(y)
    ax.set_yticklabels(d.company, fontsize=9)
    for yi, v in zip(y, d.valuation_busd_cb):
        ax.text(v + d.valuation_busd_cb.max() * 0.012, yi, f"${v:,.0f}B", va="center", fontsize=8.5)
    ax.set_xlim(0, d.valuation_busd_cb.max() * 1.18)
    ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}B"))
    ax.grid(axis="x", color="#E4E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_title("Where the private AI money is", loc="left",
                 fontsize=15, fontweight="bold", pad=18)
    ax.text(0, 1.02, "Largest private AI companies by last-round valuation (CB Insights)",
            transform=ax.transAxes, fontsize=10, color="#4A5568")
    fig.text(0, -0.02, "Private marks, not tradable prices; only companies on the CB unicorn board.",
             fontsize=7.5, color=MUTED)
    fig.savefig(OUT / "ai04_valuations.png", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    modalities()
    valuations()
    print("wrote ai company charts")
