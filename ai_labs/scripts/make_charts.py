"""Charts for the AI labs dataset."""

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
df = pd.read_csv(BASE / "data" / "ai_labs.csv")

INK, OPEN, PARTIAL, CLOSED, MUTED, BG = "#0B2545", "#5C9E6E", "#E9C46A", "#9AA5B1", "#9AA5B1", "#FFFFFF"
plt.rcParams.update({
    "font.family": "Segoe UI", "figure.facecolor": BG, "axes.facecolor": BG,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK, "ytick.color": INK, "figure.dpi": 200, "savefig.dpi": 200,
})


def by_country() -> None:
    piv = (df.assign(ow=df.open_weights)
             .pivot_table(index="country", columns="ow", values="lab",
                          aggfunc="count", fill_value=0))
    piv["total"] = piv.sum(axis=1)
    piv = piv.nlargest(12, "total").sort_values("total")
    cols = ["yes", "partial", "no"]
    colors = {"yes": OPEN, "partial": PARTIAL, "no": CLOSED}
    labels = {"yes": "Open weights", "partial": "Partial / mixed", "no": "Closed"}

    fig, ax = plt.subplots(figsize=(9, 5.6))
    left = np.zeros(len(piv))
    for c in cols:
        vals = piv.get(c, pd.Series(0, index=piv.index)).values
        ax.barh(piv.index, vals, left=left, color=colors[c], label=labels[c], height=0.65)
        left += vals
    for i, total in enumerate(piv["total"].values):
        ax.text(total + 0.4, i, str(int(total)), va="center", fontsize=9)
    ax.set_xlim(0, piv["total"].max() * 1.15)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.grid(axis="x", color="#E4E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_title("Who builds AI models, and how openly", loc="left",
                 fontsize=15, fontweight="bold", pad=18)
    ax.text(0, 1.02, "AI labs in the dataset by country, split by open-weight policy",
            transform=ax.transAxes, fontsize=10, color="#4A5568")
    fig.text(0, -0.02, "Curation: 99 notable labs and institutes; not an exhaustive census.",
             fontsize=7.5, color=MUTED)
    fig.savefig(OUT / "ai01_labs_by_country.png", bbox_inches="tight")
    plt.close(fig)


def open_reach() -> None:
    d = df.dropna(subset=["hf_top_downloads"]).nlargest(15, "hf_top_downloads")
    d = d.sort_values("hf_top_downloads")
    fig, ax = plt.subplots(figsize=(9, 5.4))
    y = np.arange(len(d))
    ax.barh(y, d.hf_top_downloads, color=OPEN, height=0.65)
    ax.set_yticks(y)
    ax.set_yticklabels(d.lab, fontsize=9)
    for yi, v in zip(y, d.hf_top_downloads):
        ax.text(v * 1.02, yi, f"{v/1e6:,.0f}M", va="center", fontsize=8.5)
    ax.set_xscale("log")
    ax.set_xlim(5e4, 2e8)
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(
        lambda x, _: f"{x/1e6:,.0f}M" if x >= 1e6 else f"{x/1e3:,.0f}k"))
    ax.grid(axis="x", color="#E4E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_title("Open weights travel", loc="left", fontsize=15, fontweight="bold", pad=18)
    ax.text(0, 1.02, "Monthly downloads of each lab's most-downloaded Hugging Face model",
            transform=ax.transAxes, fontsize=10, color="#4A5568")
    fig.text(0, -0.02, "Source: Hugging Face API (log scale). Downloads measure usage, not quality.",
             fontsize=7.5, color=MUTED)
    fig.savefig(OUT / "ai02_open_reach.png", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    by_country()
    open_reach()
    print("wrote ai lab charts")
