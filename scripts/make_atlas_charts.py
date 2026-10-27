"""Atlas charts: the shape of business on earth."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import squarify

OUT = Path("output/charts")
OUT.mkdir(parents=True, exist_ok=True)

INK, BAR, ACCENT, MUTED, BG = "#0B2545", "#1B6CA8", "#E07A4F", "#9AA5B1", "#FFFFFF"
plt.rcParams.update({
    "font.family": "Segoe UI", "figure.facecolor": BG, "axes.facecolor": BG,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK, "ytick.color": INK, "figure.dpi": 200, "savefig.dpi": 200,
})

SECTOR_COLORS = {
    "Financials": "#0B2545", "Energy & Utilities": "#1B6CA8", "Technology": "#E07A4F",
    "Consumer & Retail": "#5C9E6E", "Construction & Real Estate": "#B084CC",
    "Materials & Chemicals": "#8D6E63", "Healthcare": "#2A9D8F",
    "Food & Agriculture": "#E9C46A", "Transport & Logistics": "#6C8EBF",
    "Telecom & Media": "#C06C84", "Business Services": "#84A98C",
    "Industrials & Defense": "#4A5568", "Conglomerates": "#A0AEC0",
}


def money(v_musd: float) -> str:
    if abs(v_musd) >= 1e6:
        return f"${v_musd/1e6:,.2f}T"
    return f"${v_musd/1e3:,.0f}B"


def chart_treemap() -> None:
    df = pd.read_csv("data/global2000_2025.csv")
    sec = (df.groupby("sector", as_index=False)
             .agg(revenue=("revenue_musd", "sum"), n=("company", "count"))
             .sort_values("revenue", ascending=False))
    total = sec["revenue"].sum()
    sec["share"] = sec["revenue"] / total * 100

    fig, ax = plt.subplots(figsize=(11, 6.6))
    labels = []
    for r in sec.itertuples():
        if r.share < 1.2:
            labels.append("")  # too small to label legibly
        else:
            labels.append(f"{r.sector}\n{money(r.revenue)}  ·  {r.share:.0f}%\n{int(r.n)} companies")
    squarify.plot(
        sizes=sec["revenue"].values,
        label=labels,
        color=[SECTOR_COLORS.get(s, MUTED) for s in sec["sector"]],
        ax=ax,
        text_kwargs={"color": "white", "fontsize": 9, "fontweight": "bold"},
        pad=True,
    )
    ax.axis("off")
    ax.set_title("The map of big business", loc="left", fontsize=16, fontweight="bold", pad=22)
    ax.text(0, 1.02, "Global 2000 companies by sector, FY2024 revenue (USD)",
            transform=ax.transAxes, fontsize=10, color="#4A5568", va="bottom")
    fig.text(0, 0.01, "Source: Forbes Global 2000 (2025). Area proportional to revenue. "
                      "Sectors under 1.2% are unlabelled.",
             fontsize=8, color=MUTED)
    fig.savefig(OUT / "09_sector_treemap.png", bbox_inches="tight")
    plt.close(fig)


def chart_economy_split() -> None:
    m = pd.read_csv("data/world_macro.csv")
    latest = m.sort_values("year").groupby("indicator").tail(1).set_index("indicator")["value"]

    gdp = {"Agriculture": latest["NV.AGR.TOTL.ZS"], "Industry": latest["NV.IND.TOTL.ZS"],
           "Services": latest["NV.SRV.TOTL.ZS"]}
    emp = {"Agriculture": latest["SL.AGR.EMPL.ZS"], "Industry": latest["SL.IND.EMPL.ZS"],
           "Services": latest["SL.SRV.EMPL.ZS"]}
    colors = {"Agriculture": "#E9C46A", "Industry": "#1B6CA8", "Services": "#E07A4F"}

    fig, ax = plt.subplots(figsize=(10, 4.4))
    fig.subplots_adjust(top=0.72, bottom=0.28)
    for row, data, label in [(1, gdp, "Share of world GDP"),
                             (0, emp, "Share of world employment")]:
        left = 0
        for k, v in data.items():
            ax.barh(row, v, left=left, color=colors[k], height=0.55,
                    edgecolor="white", linewidth=1.5)
            if v > 6:
                ax.text(left + v / 2, row, f"{v:.0f}%", ha="center", va="center",
                        color="white", fontsize=11, fontweight="bold")
            left += v
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["Employment\n(3.7B workers)", "GDP\n($111.7T)"], fontsize=10)
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("{x:.0f}%"))
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    handles = [plt.Rectangle((0, 0), 1, 1, color=colors[k]) for k in gdp]
    ax.legend(handles, list(gdp.keys()), frameon=False, ncol=3,
              loc="upper center", bbox_to_anchor=(0.5, -0.22), fontsize=9)
    fig.text(0.01, 0.94, "What the world does vs what it earns", fontsize=15,
             fontweight="bold", color=INK)
    fig.text(0.01, 0.885, "Agriculture, industry and services, 2024", fontsize=10,
             color="#4A5568")
    fig.text(0.01, 0.02, "Source: World Bank Open Data (2024)", fontsize=8, color=MUTED)
    fig.savefig(OUT / "10_gdp_vs_employment.png", bbox_inches="tight")
    plt.close(fig)


def chart_concentration() -> None:
    df = pd.read_csv("data/global2000_2025.csv")
    rev = df["revenue_musd"].sort_values(ascending=False).values
    cum = np.cumsum(rev) / rev.sum() * 100
    ranks = np.arange(1, len(rev) + 1)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(ranks, cum, color=BAR, linewidth=2.4)
    ax.fill_between(ranks, cum, color=BAR, alpha=0.12)
    for k in (10, 100, 1000):
        ax.plot([k], [cum[k - 1]], "o", color=ACCENT, markersize=6)
        ax.annotate(f"top {k:,}: {cum[k-1]:.0f}%", (k, cum[k - 1]),
                    xytext=(8, -14), textcoords="offset points", fontsize=9, color=INK)
    ax.set_xscale("log")
    ax.set_xlim(1, len(rev))
    ax.set_ylim(0, 105)
    ax.set_xlabel("Company rank by revenue (log scale)", fontsize=10)
    ax.set_ylabel("Cumulative share of revenue", fontsize=10)
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter("{x:.0f}%"))
    ax.grid(color="#E4E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_title("A very short head", loc="left", fontsize=15, fontweight="bold", pad=16)
    ax.text(0, 1.03, "How much of the 2,000 companies' $52.9T revenue the largest firms hold",
            transform=ax.transAxes, fontsize=10, color="#4A5568")
    fig.text(0, -0.02, "Source: Forbes Global 2000 (2025)", fontsize=8, color=MUTED)
    fig.savefig(OUT / "11_concentration.png", bbox_inches="tight")
    plt.close(fig)


def chart_country_gap() -> None:
    df = pd.read_csv("data/global2000_2025.csv")
    gdp = pd.read_csv("data/country_gdp_2024.csv")

    # align country names: Forbes vs World Bank
    alias = {"Korea, Rep.": "South Korea", "Russian Federation": "Russia",
             "Turkiye": "Turkey", "Türkiye": "Turkey", "Viet Nam": "Vietnam",
             "Iran, Islamic Rep.": "Iran", "Egypt, Arab Rep.": "Egypt"}
    gdp["country"] = gdp["country"].replace(alias)

    gdp_share = gdp.set_index("country")["gdp_usd"] / gdp["gdp_usd"].sum() * 100
    forbes_share = (df.groupby("country")["revenue_musd"].sum() / df["revenue_musd"].sum() * 100)

    countries = gdp.head(10)["country"].tolist()
    fig, ax = plt.subplots(figsize=(10, 5.6))
    fig.subplots_adjust(top=0.80)
    x = np.arange(len(countries))
    w = 0.38
    g = [gdp_share.get(c, 0) for c in countries]
    f = [forbes_share.get(c, 0) for c in countries]
    ax.bar(x - w / 2, g, w, label="Share of world GDP", color=MUTED)
    ax.bar(x + w / 2, f, w, label="Share of Global 2000 revenue", color=BAR)
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace("Korea, Rep.", "South Korea") for c in countries],
                       rotation=25, ha="right", fontsize=9)
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter("{x:.0f}%"))
    ax.grid(axis="y", color="#E4E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    fig.text(0.01, 0.955, "Two ways of counting an economy", fontsize=15,
             fontweight="bold", color=INK)
    fig.text(0.01, 0.905, "Top 10 economies: GDP share vs share of the 2,000 companies' revenue",
             fontsize=10, color="#4A5568")
    fig.text(0, -0.06, "Sources: World Bank (2024 GDP), Forbes Global 2000 (2025)",
             fontsize=8, color=MUTED)
    fig.savefig(OUT / "12_country_gap.png", bbox_inches="tight")
    plt.close(fig)


def chart_invisible() -> None:
    m = pd.read_csv("data/companies_master.csv")
    outside = m[m["source"].str.startswith("Fortune")]
    order = ["State-owned", "Private", "Mutual / Cooperative", "Public (outside Forbes)"]
    colors = {"State-owned": "#0B2545", "Mutual / Cooperative": "#5C9E6E",
              "Private": "#E07A4F", "Public (outside Forbes)": "#9AA5B1"}
    agg = outside.groupby("ownership").agg(
        revenue=("revenue_musd", "sum"), n=("company", "count")
    ).reindex(order)

    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    fig.subplots_adjust(top=0.72, left=0.28)
    y = np.arange(len(agg))[::-1]
    vals = (agg["revenue"] / 1e6).values
    ax.barh(y, vals, color=[colors[k] for k in agg.index], height=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{k}\n{int(n)} companies" for k, n in zip(agg.index, agg["n"])],
                       fontsize=9.5)
    for yi, v in zip(y, vals):
        ax.text(v + 0.08, yi, f"${v:,.2f}T", va="center", fontsize=10, fontweight="bold")
    ax.set_xlim(0, max(vals) * 1.18)
    ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.1f}T"))
    ax.grid(axis="x", color="#E4E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)

    fig.text(0.01, 0.93, "The $6.4 trillion the public list leaves out", fontsize=15,
             fontweight="bold", color=INK)
    fig.text(0.01, 0.875, "90 large companies outside the Forbes 2000, by ownership "
                          "and revenue", fontsize=10, color="#4A5568")
    fig.text(0.01, 0.02, "For scale, the 2,000 listed companies together report $52.9T of "
                         "revenue.  Sources: Fortune Global 500 (2025); ownership labels "
                         "are manual.", fontsize=7.5, color=MUTED)
    fig.savefig(OUT / "13_invisible_giants.png", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    chart_treemap()
    chart_economy_split()
    chart_concentration()
    chart_country_gap()
    chart_invisible()
    print("wrote atlas charts")
