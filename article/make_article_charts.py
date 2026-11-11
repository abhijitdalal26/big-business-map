"""Charts for the first Substack essay (article/essay_01_draft.md).

Run from the repo root:
    python article/essay_numbers.py 2026      (first: computes the numbers)
    python article/make_article_charts.py [year]

Writes PNGs to article/images/. Uses the same colours and fonts as
data_analysis/style.py so the essay matches the study pack and the site.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
# Every Forbes-based number comes from essay_numbers.py, so charts and text always agree.
N = json.loads((ROOT / f"article/data/essay_numbers_{YEAR}.json").read_text(encoding="utf-8"))
OUT = ROOT / "article" / "images"
OUT.mkdir(parents=True, exist_ok=True)

INK = "#0B2545"
BAR = "#1B6CA8"
ACCENT = "#E07A4F"
MUTED = "#9AA5B1"
GREEN = "#5DA06E"
SAND = "#E8C46C"
GRID = "#E6EAF0"

plt.rcParams.update({
    "font.family": "Segoe UI",
    "font.size": 11,
    "axes.edgecolor": "#C9D2DD",
    "text.color": INK,
    "axes.labelcolor": INK,
    "xtick.color": "#4A5563",
    "ytick.color": "#4A5563",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
    "savefig.facecolor": "white",
})


def titles(fig, title: str, subtitle: str, source: str) -> None:
    fig.text(0.01, 0.98, title, fontsize=18, fontweight="bold", color=INK, va="top")
    sub_y = 0.98 - 0.42 / fig.get_figheight()  # keep a fixed gap below the title
    fig.text(0.01, sub_y, subtitle, fontsize=12, color="#4A5563", va="top")
    fig.text(0.01, 0.01, source, fontsize=8.5, color=MUTED, va="bottom")


def save(fig, name: str) -> None:
    fig.savefig(OUT / name)
    plt.close(fig)
    print("wrote", name)


# 1. The pyramid of business --------------------------------------------------
def pyramid() -> None:
    levels = [
        ("Businesses on Earth (mostly informal)", "~400 million", 400e6, SAND),
        ("Formally registered small & mid firms", "322 million+", 322e6, "#D9B65F"),
        ("Companies listed on a stock exchange", "47,980", 47_980, BAR),
        ("Forbes Global 2000 giants", "2,000", 2_000, INK),
        ("Companies worth $1 trillion+ (Oct 2026)", "15", 15, ACCENT),
    ]
    fig, ax = plt.subplots(figsize=(10, 6.2))
    fig.subplots_adjust(top=0.82, bottom=0.08)
    import math
    max_w = math.log10(levels[0][2])
    for i, (label, n_txt, n, colour) in enumerate(levels):
        w = math.log10(n) / max_w  # width on a log scale, else the top is invisible
        y = len(levels) - i
        ax.barh(y, w, left=-w / 2, height=0.82, color=colour)
        if w > 0.25:
            ax.text(0, y + 0.08, n_txt, ha="center", va="center", fontsize=15,
                    fontweight="bold", color="white" if i >= 2 else INK)
            ax.text(0, y - 0.24, label, ha="center", va="center", fontsize=9.5,
                    color="white" if i >= 2 else INK)
        else:  # too narrow: number inside, label beside
            ax.text(0, y, n_txt, ha="center", va="center", fontsize=15,
                    fontweight="bold", color="white")
            ax.text(w / 2 + 0.02, y, label, ha="left", va="center", fontsize=9.5)
    ax.set_xlim(-0.55, 0.78)
    ax.axis("off")
    ax.text(0.53, 3.5, "1 listed company\nfor every ~8,000\nbusinesses",
            ha="left", va="center", fontsize=10, color="#4A5563", style="italic")
    titles(fig, "The pyramid of business on Earth",
           "Each step is a different count from a different source. Bar widths are on a log scale.",
           "Sources: IFC/McKinsey via CGAP (2010 est.); IFC SME Finance Forum (2019); "
           "World Bank CM.MKT.LDOM.NO (2024); "
           f"Forbes Global 2000 ({YEAR}); CompaniesMarketCap (Oct 2026).")
    save(fig, "01_pyramid_of_business.png")


# 2. How few firms make half of everything -----------------------------------
def half_of_everything() -> None:
    t, h = N["totals"], N["half_of"]
    rows = [(f"Revenue\n(${t['rev_T']:.1f}T)", h["revenue"]), (f"Profit\n(${t['profit_T']:.1f}T)", h["profit"]),
            (f"Market value\n(${t['mv_T']:.1f}T)", h["market_value"])]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    fig.subplots_adjust(top=0.76, bottom=0.12, left=0.16)
    labels = [r[0] for r in rows][::-1]
    vals = [r[1] for r in rows][::-1]
    ax.barh(labels, [2000] * 3, color=GRID, height=0.6)
    ax.barh(labels, vals, color=[ACCENT, BAR, BAR][::-1], height=0.6)
    for y, v in enumerate(vals):
        ax.text(v + 25, y, f"{v} companies hold half", va="center", fontsize=11,
                fontweight="bold", color=INK)
    ax.set_xlim(0, 2000)
    ax.set_xticks([0, 500, 1000, 1500, 2000])
    ax.grid(axis="x", color=GRID)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0, labelsize=11)
    titles(fig, "Half of everything, a handful of firms",
           "Out of the 2,000 biggest listed companies, how many it takes to reach 50% of the total",
           f"Source: Forbes Global 2000 ({YEAR} list; latest fiscal-year financials, market value at list date).")
    save(fig, "02_half_of_everything.png")


# 3. Where profit is made vs where value is priced ---------------------------
def sector_shares() -> None:
    s = pd.DataFrame(N["sectors"])
    s["revenue_share"], s["profit_share"], s["value_share"] = s.rev_pct / 100, s.pro_pct / 100, s.mv_pct / 100
    keep = ["Technology", "Financials", "Consumer & Retail", "Energy & Utilities", "Healthcare"]
    s = s.set_index("sector").loc[keep[::-1]]
    fig, ax = plt.subplots(figsize=(10, 5.8))
    fig.subplots_adjust(top=0.80, bottom=0.12, left=0.2)
    h = 0.26
    y = range(len(s))
    for off, col, colour, name in [(h, "revenue_share", MUTED, "Share of revenue"),
                                   (0, "profit_share", BAR, "Share of profit"),
                                   (-h, "value_share", ACCENT, "Share of market value")]:
        ax.barh([i + off for i in y], s[col] * 100, height=h, color=colour, label=name)
        for i, v in zip(y, s[col] * 100):
            ax.text(v + 0.4, i + off, f"{v:.0f}%", va="center", fontsize=9)
    ax.set_yticks(list(y))
    ax.set_yticklabels(s.index, fontsize=11)
    ax.tick_params(axis="y", length=0)
    ax.xaxis.set_major_formatter(lambda x, _: f"{x:.0f}%")
    ax.grid(axis="x", color=GRID)
    ax.set_axisbelow(True)
    ax.legend(loc="lower right", frameon=False, fontsize=10)
    titles(fig, "Profit is made in banks. Value is priced in tech.",
           "Each sector's share of the Global 2000's revenue, profit and market value",
           f"Source: Forbes Global 2000 ({YEAR}). Bank 'revenue' is gross interest + fees, which inflates Financials.")
    save(fig, "03_profit_vs_value_by_sector.png")


# 4. The true top 15 by revenue, listed or not --------------------------------
def true_top() -> None:
    # The same re-ranked list the site's Scale page shows (Forbes listed + Fortune unlisted).
    kind = {"Listed (in Forbes)": "Listed company", "State-owned": "State-owned, no shares traded",
            "Private": "Privately owned", "Mutual/co-op": "Member-owned"}
    top = pd.DataFrame(N["true_top15"]).rename(columns={"name": "company"})
    top["revenue_musd"] = top.rev_B * 1000
    top["kind"] = top.owner.map(kind).fillna("Listed company")
    top = top.iloc[::-1]
    top["company"] = top.company.replace({"Saudi Arabian Oil Company (Saudi Aramco)": "Saudi Aramco",
                                          "China National Petroleum": "China National Petroleum (CNPC)"})
    colours = {"Listed company": BAR, "State-owned, no shares traded": ACCENT,
               "Privately owned": GREEN, "Member-owned": SAND}
    fig, ax = plt.subplots(figsize=(10, 7))
    fig.subplots_adjust(top=0.84, bottom=0.08, left=0.3)
    ax.barh(top.company, top.revenue_musd / 1000, color=[colours[k] for k in top.kind], height=0.7)
    for i, (v, k) in enumerate(zip(top.revenue_musd / 1000, top.kind)):
        ax.text(v + 5, i, f"${v:,.0f}B", va="center", fontsize=9.5,
                fontweight="bold" if k != "Listed company" else "normal")
    ax.tick_params(axis="y", length=0, labelsize=10.5)
    ax.xaxis.set_major_formatter(lambda x, _: f"${x:,.0f}B")
    ax.grid(axis="x", color=GRID)
    ax.set_axisbelow(True)
    handles = [plt.Rectangle((0, 0), 1, 1, color=colours[k]) for k in
               ["Listed company", "State-owned, no shares traded"]]
    ax.legend(handles, ["Listed (in Forbes Global 2000)", "State-owned, no shares traded"],
              loc="lower right", frameon=False, fontsize=10)
    titles(fig, "The world's biggest companies, if you include the ones with no ticker",
           "Top 15 by revenue. The orange bars never show up on a stock screen.",
           f"Sources: Forbes Global 2000 ({YEAR}) for listed firms; Fortune Global 500 for unlisted ones. "
           "Latest fiscal-year revenue. Ownership labels are curated.")
    save(fig, "04_true_top15_by_revenue.png")


# 5. How the world's workers actually work -----------------------------------
def employment_status() -> None:
    rows = [("Employees", 52.3, BAR), ("Own-account\n(self-employed, no staff)", 34.7, SAND),
            ("Family\nworkers", 9.8, GREEN), ("Employers", 3.2, ACCENT)]
    fig, ax = plt.subplots(figsize=(10, 4.4))
    fig.subplots_adjust(top=0.76, bottom=0.12)
    left = 0
    for label, v, colour in rows:
        ax.barh(0, v, left=left, color=colour, height=0.55, edgecolor="white", linewidth=2)
        cx = left + v / 2
        if v > 8:
            ax.text(cx, 0, f"{v:.0f}%", ha="center", va="center", color="white",
                    fontsize=15, fontweight="bold")
            ax.text(cx, -0.48, label, ha="center", va="top", fontsize=9.5)
        else:
            ax.text(cx, 0.42, f"{label} {v:.0f}%", ha="center", va="bottom", fontsize=9.5)
        left += v
    ax.set_xlim(0, 100)
    ax.set_ylim(-1.1, 0.75)
    ax.axis("off")
    titles(fig, "Only half the world's workers have a boss",
           "World employment by status. 58% of all jobs are informal (about 2 billion people).",
           "Source: ILO modelled estimates, 'World: informality regional statistical profile' (2025).")
    save(fig, "05_how_the_world_works.png")


# 6. AI is eating venture capital ---------------------------------------------
def ai_share_of_vc() -> None:
    v = pd.read_csv(ROOT / "site/build/context_data/vc_ai_share_crunchbase.csv")
    fig, ax = plt.subplots(figsize=(10, 4.8))
    fig.subplots_adjust(top=0.78, bottom=0.12)
    colours = [MUTED, MUTED, BAR, ACCENT]
    ax.bar(v.period.astype(str), v.share, color=colours, width=0.6)
    for i, (s, ai, tot) in enumerate(zip(v.share, v.ai, v.total)):
        ax.text(i, s + 1.5, f"{s:.0f}%", ha="center", fontsize=15, fontweight="bold")
        ax.text(i, s / 2, f"${ai:.0f}B\nof ${tot:.0f}B", ha="center", va="center",
                color="white", fontsize=9.5)
    ax.set_ylim(0, 75)
    ax.yaxis.set_major_formatter(lambda x, _: f"{x:.0f}%")
    ax.grid(axis="y", color=GRID)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", length=0, labelsize=12)
    titles(fig, "AI is eating venture capital",
           "Share of global venture funding that went to AI companies",
           "Source: Crunchbase News (year-end 2024 and 2025 reviews; Q3 2026 report, 5 Oct 2026).")
    save(fig, "06_ai_share_of_vc.png")


# 7. The higher up the pyramid, the more American --------------------------------
def us_share() -> None:
    u = N["us"]
    rows = [("World GDP", u["gdp_pct"], "World Bank, 2024"),
            ("Global 2000 revenue", u["rev_pct"], f"Forbes, {YEAR} list"),
            ("Global 2000 profit", u["pro_pct"], f"Forbes, {YEAR} list"),
            ("Global 2000 market value", u["mv_pct"], f"Forbes, {YEAR} list"),
            ("Unicorn value", u["unicorn_value_pct"], "CB Insights, 2026")]
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.subplots_adjust(top=0.78, bottom=0.1, left=0.25)
    labels = [r[0] for r in rows][::-1]
    vals = [r[1] for r in rows][::-1]
    colours = [ACCENT if v >= 50 else BAR for v in vals]
    colours[-1] = MUTED  # GDP is the yardstick
    ax.barh(labels, [100] * len(rows), color=GRID, height=0.6)
    ax.barh(labels, vals, color=colours, height=0.6)
    for y, (v, (_, _, src)) in enumerate(zip(vals, rows[::-1])):
        ax.text(v + 1.2, y, f"{v:.0f}%", va="center", fontsize=13, fontweight="bold", color=INK)
        ax.text(99, y, src, va="center", ha="right", fontsize=8.5, color="#4A5563")
    ax.axvline(50, color=INK, linewidth=0.8, linestyle=(0, (3, 3)))
    ax.set_xlim(0, 100)
    ax.set_xticks([])
    ax.tick_params(axis="y", length=0, labelsize=11)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_visible(False)
    titles(fig, "The higher up the pyramid, the more American",
           "United States' share of each measure. The dashed line is half the world.",
           "Sources as labelled. Country = headquarters. Unicorn value = last private-round marks.")
    save(fig, "11_more_american.png")


# 8. The giants with no shares to buy -------------------------------------------
def unlisted_giants() -> None:
    mix = {r["owner"]: r for r in N["ownership"]["fortune_mix"]}
    rows = [("State-owned, unlisted", "State-owned", ACCENT),
            ("Private (family / founder / foundation)", "Private", GREEN),
            ("Mutual / co-operative", "Member-owned (mutual / co-op)", SAND)]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    fig.subplots_adjust(top=0.76, bottom=0.12, left=0.27)
    labels, vals, cols = [], [], []
    for key, label, colour in rows[::-1]:
        r = mix[key]
        labels.append(f"{label}\n{r['n']} companies")
        vals.append(r["rev"] / 1e6)
        cols.append(colour)
    ax.barh(labels, vals, color=cols, height=0.62)
    for y, v in enumerate(vals):
        ax.text(v + 0.08, y, f"${v:.1f}T", va="center", fontsize=13, fontweight="bold", color=INK)
    ax.set_xlim(0, max(vals) * 1.2)
    ax.xaxis.set_major_formatter(lambda x, _: f"${x:.0f}T")
    ax.grid(axis="x", color=GRID)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0, labelsize=11)
    o = N["ownership"]
    titles(fig, f"${o['unlisted_rev'] / 1e6:.1f} trillion a year, and no shares to buy",
           f"{o['unlisted_n']} of the world's 500 largest companies by revenue have no listed shares at group level",
           "Source: Fortune Global 500, ownership labels curated by the atlas (as on the site's Ownership page).")
    save(fig, "08_unlisted_giants.png")


# Reused charts from the existing pack ------------------------------------------
def copy_existing() -> None:
    for src, dst in [("output/charts/10_gdp_vs_employment.png", "07_gdp_vs_employment.png")]:
        shutil.copy(ROOT / src, OUT / dst)
        print("copied", dst)


if __name__ == "__main__":
    pyramid()
    half_of_everything()
    sector_shares()
    true_top()
    employment_status()
    ai_share_of_vc()
    us_share()
    unlisted_giants()
    copy_existing()
