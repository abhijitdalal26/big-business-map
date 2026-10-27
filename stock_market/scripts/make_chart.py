"""Chart for the stock-exchange view."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
e = pd.read_csv(BASE / "data" / "exchanges.csv")
OUT = BASE / "charts"
OUT.mkdir(parents=True, exist_ok=True)

INK, BAR, ACCENT, MUTED, BG = "#0B2545", "#1B6CA8", "#E07A4F", "#9AA5B1", "#FFFFFF"
plt.rcParams.update({
    "font.family": "Segoe UI", "figure.facecolor": BG, "axes.facecolor": BG,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK, "ytick.color": INK, "figure.dpi": 200, "savefig.dpi": 200,
})

top = e.nlargest(20, "total_market_cap_usd").sort_values("total_market_cap_usd")
labels = top["exchange"]
values = top["total_market_cap_usd"] / 1e12

fig, ax = plt.subplots(figsize=(9.5, 6.4))
y = np.arange(len(top))
ax.barh(y, values, color=BAR, height=0.65)
ax.barh(y[-2:], values[-2:], color=ACCENT, height=0.65)  # highlight US
ax.set_yticks(y)
ax.set_yticklabels(labels, fontsize=9)
for yi, v, n in zip(y, values, top["companies"]):
    ax.text(v + max(values) * 0.01, yi, f"${v:,.1f}T  ({n:,})", va="center", fontsize=8.5)
ax.set_xlim(0, max(values) * 1.22)
ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}T"))
ax.grid(axis="x", color="#E4E7EB", linewidth=0.8)
ax.set_axisbelow(True)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.tick_params(axis="y", length=0)
ax.set_title("The world's stock markets, ranked", loc="left", fontsize=15,
             fontweight="bold", pad=18)
ax.text(0, 1.02, "Total market value of the companies we can see, by exchange "
                 "(company count in brackets)", transform=ax.transAxes,
        fontsize=10, color="#4A5568")
fig.text(0, -0.02, "Source: companiesmarketcap + SEC. Coverage is the top ~10,000 listed "
                   "companies, not every listing on each exchange.", fontsize=7.5, color=MUTED)
fig.savefig(OUT / "sm01_exchanges_market_cap.png", bbox_inches="tight")
plt.close(fig)
print("wrote chart")
