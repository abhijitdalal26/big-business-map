"""The 'business idea' layer for the essay.

For every company in the Forbes Global 2000, plus the unlisted giants from the
Fortune Global 500 and Forbes' largest US private companies, this writes:

  article/data/business_ideas.csv   one row per company with a one-line "what they do"
  article/data/idea_sectors.csv     per sector: how far the idea scales, margins, value
  article/images/09_idea_fingerprint_world.png      spider chart, revenue vs value
  article/images/10_idea_fingerprint_countries.png  spider small multiples by country

Sectors are the same 13 used by the site's "What the 2,000 actually do" treemap
(scripts/taxonomy.py), so the essay and the site never disagree on categories.

Run from the repo root:  python article/business_ideas.py [year]   (default 2025)
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
DATA_OUT = ROOT / "article" / "data"
IMG_OUT = ROOT / "article" / "images"
DATA_OUT.mkdir(parents=True, exist_ok=True)

INK, BAR, ACCENT, MUTED, GRID = "#0B2545", "#1B6CA8", "#E07A4F", "#9AA5B1", "#E6EAF0"
plt.rcParams.update({"font.family": "Segoe UI", "text.color": INK,
                     "savefig.dpi": 200, "savefig.bbox": "tight", "savefig.facecolor": "white"})

# Order round the spider: related ideas sit next to each other.
# Conglomerates (8 firms, 0.5% of revenue) are left off the charts.
AXES = ["Financials", "Business Services", "Technology", "Telecom & Media", "Healthcare",
        "Consumer & Retail", "Food & Agriculture", "Transport & Logistics",
        "Industrials & Defense", "Construction & Real Estate", "Materials & Chemicals",
        "Energy & Utilities"]
SHORT = {"Financials": "Money", "Business Services": "Services\n& trading",
         "Technology": "Tech", "Telecom & Media": "Telecom\n& media", "Healthcare": "Health",
         "Consumer & Retail": "Consumer\n& retail", "Food & Agriculture": "Food",
         "Transport & Logistics": "Transport", "Industrials & Defense": "Machines\n& defence",
         "Construction & Real Estate": "Building\n& property", "Materials & Chemicals": "Materials",
         "Energy & Utilities": "Energy"}

# The idea behind each sector, in one sentence: how the money is made.
IDEA = {
    "Financials": "Hold other people's money and earn the spread: lend deposits, invest premiums, charge fees.",
    "Business Services": "Do work companies don't want to do themselves, or buy and resell goods in bulk.",
    "Technology": "Write code or design chips once, then sell copies at almost no extra cost.",
    "Telecom & Media": "Own the pipes or the content, and charge everyone who wants to use them.",
    "Healthcare": "Sell treatments, devices or insurance to people who can't say no.",
    "Consumer & Retail": "Make or stock what households buy, and win on brand or volume.",
    "Food & Agriculture": "Turn crops and animals into branded food and drink, or sell groceries.",
    "Transport & Logistics": "Move people and goods, with planes, ships, trucks and rail.",
    "Industrials & Defense": "Build the machines other businesses and governments run on.",
    "Construction & Real Estate": "Build things that stay put, and own or rent them out.",
    "Materials & Chemicals": "Turn rocks, ores and oil into steel, cement, plastics and chemicals.",
    "Energy & Utilities": "Dig up, refine or generate energy and sell it by the unit.",
    "Conglomerates": "Own many unrelated businesses under one roof.",
}

# --- one-line "what they do" ---------------------------------------------------
ABBR = re.compile(r"\b(Co|Cos|Inc|Corp|Ltd|Bhd|Plc|PLC|Bros|Jr|St|No|Mfg|Intl|Hldgs|Grp|"
                  r"S\.A|N\.V|A\.G|S\.p\.A|S\.A\.B|de C\.V|B\.V|U\.S|U\.K|K\.K|Tbk|Pt|P\.L\.C)\.")
NOUN_TO_VERB = {"provision": "provides", "manufacture": "makes", "manufacturing": "makes",
                "development": "develops", "production": "produces", "sale": "sells",
                "sales": "sells", "operation": "operates", "distribution": "distributes",
                "design": "designs", "exploration": "explores", "generation": "generates",
                "supply": "supplies", "management": "manages", "construction": "builds",
                "processing": "processes", "retail": "retails", "marketing": "markets",
                "research": "researches", "refining": "refines", "transmission": "transmits",
                "ownership": "owns", "investment": "invests in", "acquisition": "acquires",
                "trading": "trades", "mining": "mines", "underwriting": "underwrites"}


def first_sentence(text: str) -> str:
    t = ABBR.sub(lambda m: m.group(1).replace(".", ""), " ".join(str(text).split()))
    parts = re.split(r"(?<=[a-z0-9\)])\.\s+(?=[A-Z])", t, maxsplit=1)
    return parts[0].rstrip(".")


def idea_line(text) -> str:
    if not isinstance(text, str) or not text.strip():
        return ""
    s = first_sentence(text)
    # Forbes text sometimes drops the "in" or misspells it ("engages development", "enages in").
    m = re.search(r"\b(?:engages|enages|is engaged|are engaged|engage)\s+(?:in\s+)?(.*)", s)
    if m:
        body = m.group(1)
        m2 = re.match(r"(?:the\s+)?(\w+)\s+of\s+(.*)", body)
        if m2 and m2.group(1).lower() in NOUN_TO_VERB:
            body = f"{NOUN_TO_VERB[m2.group(1).lower()]} {m2.group(2)}"
        elif m2 and m2.group(1).lower() == "business":
            body = m2.group(2)
        else:
            body = re.sub(r"^the\s+", "", body)
    else:
        m = re.search(r"\b(?:is|was|are)\s+(?:an?|the|one of the)\s+(.*)", s)
        if m:
            body = "A " + m.group(1) if not m.group(0).startswith(("is one", "are one")) else "One of the " + m.group(1)
        else:
            m = re.search(r"\b(operates|provides|offers|manufactures|develops|designs|produces|"
                          r"sells|owns|explores|generates|distributes)\b(.*)", s)
            body = (m.group(1) + m.group(2)) if m else s
    body = body.strip(" ,;")
    body = re.sub(r"^A (?=[AEIO]|U(?!ni|kr|ser|S))", "An ", body)  # "A American" -> "An American"
    if len(body) > 170:
        body = body[:170].rsplit(" ", 1)[0].rstrip(",;") + "…"
    return body[:1].upper() + body[1:]


# --- build the company table ----------------------------------------------------
def load() -> pd.DataFrame:
    g = pd.read_csv(ROOT / f"data/global{2000}_{YEAR}.csv", encoding="utf-8-sig")
    g = g.rename(columns={"revenue_musd": "rev", "profits_musd": "profit",
                          "market_value_musd": "value"})
    g["ownership"] = "listed"
    g["list"] = f"Forbes Global 2000 ({YEAR})"
    g = g[["company", "country", "sector", "industry_canon", "ownership", "list",
           "rev", "profit", "value", "employees", "description"]]

    # Unlisted giants and big US private firms from the reconciled directory.
    d = pd.read_csv(ROOT / "data_analysis/output/data/companies__company_directory.csv")
    extra = d[(d.source.isin(["fortune", "private"])) & (d.ownership != "public")].copy()
    extra = extra.rename(columns={"revenue_usd": "rev", "profit_usd": "profit"})
    extra["rev"] /= 1e6
    extra["profit"] /= 1e6
    extra["value"] = np.nan
    extra["list"] = extra.source.map({"fortune": "Fortune Global 500 (2025)",
                                      "private": "Forbes Largest US Private (2025)"})
    extra["sector"] = extra.sector.fillna("Unclassified")
    # Fill missing descriptions from Wikipedia where the name matches exactly.
    wiki = pd.read_csv(ROOT / "listed_universe/data/wiki_descriptions.csv")
    wiki = wiki[wiki.match == True].drop_duplicates("query").set_index("query")["extract"]  # noqa: E712
    extra["description"] = extra.description.fillna(extra.company.map(wiki))
    extra = extra[["company", "country", "sector", "industry_canon", "ownership", "list",
                   "rev", "profit", "value", "employees", "description"]]

    out = pd.concat([g, extra], ignore_index=True)
    out = out[out.rev.notna()].sort_values("rev", ascending=False).reset_index(drop=True)
    out.insert(0, "rank_by_revenue", out.index + 1)
    out["company"] = out.company.str.strip().str.replace("Electricit� de France", "Électricité de France")
    out["what_they_do"] = out.description.map(idea_line)
    out["what_they_do_source"] = np.where(out.what_they_do != "", "Forbes / directory text", "")

    # Wikipedia first sentences fetched by fetch_wiki_ideas.py, for the gaps.
    cache = ROOT / "article/data/wiki_ideas.csv"
    if cache.exists():
        w = pd.read_csv(cache).dropna(subset=["extract"]).set_index("company")["extract"]
        gap = (out.what_they_do == "") & out.company.str.strip().isin(w.index)
        lines = out.loc[gap, "company"].str.strip().map(w).map(idea_line)
        lines = lines.str.replace(r"^A ((?:\w+-)?(?:largest|biggest|leading|oldest))", r"The \1", regex=True)
        # Drop search misses (list pages) and lines that only repeat the name.
        bad = (lines.str.contains(r"\blist of\b", case=False) | (lines.str.len() < 30)
               | lines.str.match(r"^A (?:wholly )?state-owned (?:holding company|enterprise)(?: of China)?(?:,| headquartered| under|$)"))
        lines[bad] = ""
        out.loc[gap, "what_they_do"] = lines
        out.loc[gap, "what_they_do_source"] = np.where(lines != "", "Wikipedia (CC BY-SA)", "")

    # Hand-written lines and sector labels win over everything else.
    ov = pd.read_csv(ROOT / "article/data/idea_overrides.csv", keep_default_na=False)
    missing = set(ov.company) - set(out.company)
    if missing:
        print("overrides used only by the site (not in this list):", len(missing))
    for r in ov.itertuples():
        m = out.company == r.company
        if r.sector:
            out.loc[m, "sector"] = r.sector
        if r.what_they_do:
            out.loc[m, "what_they_do"] = r.what_they_do
            out.loc[m, "what_they_do_source"] = "hand-written"

    out["idea_family"] = out.sector.map(IDEA).fillna("")
    return out


def sector_table(c: pd.DataFrame) -> pd.DataFrame:
    f = c[c.list.str.startswith("Forbes Global")]  # one source for shares
    rows = []
    for s, x in f.groupby("sector"):
        top = x.nlargest(3, "rev").company.tolist()
        pos = x[x.profit > 0]
        rows.append({
            "sector": s, "the_idea": IDEA.get(s, ""), "companies": len(x),
            "revenue_share": x.rev.sum() / f.rev.sum(),
            "profit_share": x.profit.sum() / f.profit.sum(),
            "value_share": x.value.sum() / f.value.sum(),
            "median_margin": (x.profit / x.rev).median(),
            "value_per_profit": x.value.sum() / pos.profit.sum() if len(pos) else np.nan,
            "n_over_100B": int((x.rev >= 100_000).sum()),
            "n_over_10B": int((x.rev >= 10_000).sum()),
            "biggest": ", ".join(top),
            # How many giants this idea has that no stock list shows
            "unlisted_giants": int(((c.sector == s) & (~c.list.str.startswith("Forbes Global"))
                                    & (c.rev >= 10_000)).sum()),
        })
    return pd.DataFrame(rows).sort_values("revenue_share", ascending=False)


# --- spider charts --------------------------------------------------------------
def spider(ax, series, rmax, show_labels=True):
    """series: list of (values-in-%, colour, label, filled)."""
    n = len(AXES)
    ang = [i / n * 2 * math.pi for i in range(n)] + [0]
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_ylim(0, rmax)
    step = 10 if rmax <= 40 else 20
    ticks = [t for t in range(step, int(rmax), step)]
    ax.set_yticks(ticks)
    ax.set_yticklabels([f"{t}%" for t in ticks], fontsize=7, color=MUTED)
    ax.set_rlabel_position(360 / n / 2)
    ax.set_xticks(ang[:-1])
    ax.set_xticklabels([SHORT[a] for a in AXES] if show_labels else [], fontsize=8.5, color="#4A5563")
    ax.tick_params(axis="x", pad=10)
    ax.grid(color=GRID, linewidth=0.8)
    ax.spines["polar"].set_color(GRID)
    for vals, colour, label, filled in series:
        v = list(vals) + [vals[0]]
        if filled:
            ax.fill(ang, v, color=colour, alpha=0.18, zorder=2)
            ax.plot(ang, v, color=colour, linewidth=2, label=label, zorder=3)
        else:
            ax.plot(ang, v, color=colour, linewidth=1.5, linestyle=(0, (4, 3)), label=label, zorder=2)


def shares(df, col):
    tot = df[col].sum()
    return [100 * df.loc[df.sector == a, col].sum() / tot for a in AXES]


def chart_world(f: pd.DataFrame) -> None:
    fig = plt.figure(figsize=(9, 9.6))
    ax = fig.add_axes([0.12, 0.08, 0.76, 0.72], polar=True)
    spider(ax, [(shares(f, "rev"), MUTED, "Share of revenue", True),
                (shares(f, "value"), ACCENT, "Share of market value", True)], rmax=30)
    ax.legend(loc="upper right", bbox_to_anchor=(1.18, 1.12), frameon=False, fontsize=10)
    rv, vv = shares(f, "rev"), shares(f, "value")
    n = len(AXES)
    for name in ("Technology", "Financials"):
        i = AXES.index(name)
        ax.annotate(f"{rv[i]:.0f}% of revenue\n{vv[i]:.0f}% of value",
                    xy=(i / n * 2 * math.pi, max(rv[i], vv[i])),
                    xytext=(14, -34) if name == "Technology" else (14, 4),
                    textcoords="offset points", fontsize=9.5, fontweight="bold", color=INK)
    fig.text(0.02, 0.98, "Which business ideas the world pays for", fontsize=18,
             fontweight="bold", color=INK, va="top")
    fig.text(0.02, 0.935, "Each spoke is one kind of business. Grey: where the money comes in. "
             "Orange: what investors value.", fontsize=11.5, color="#4A5563", va="top")
    fig.text(0.02, 0.01, f"Source: Forbes Global 2000 ({YEAR}), sectors as on the site "
             "(scripts/taxonomy.py). Conglomerates (0.5%) not shown.", fontsize=8.5, color=MUTED)
    fig.savefig(IMG_OUT / "09_idea_fingerprint_world.png")
    plt.close(fig)
    print("wrote 09_idea_fingerprint_world.png")


def chart_countries(f: pd.DataFrame) -> None:
    groups = [("United States", f.country == "United States"),
              ("China (mainland)", f.country == "China"),
              ("Japan", f.country == "Japan"),
              ("India", f.country == "India"),
              ("Germany", f.country == "Germany"),
              ("Saudi Arabia & Gulf", f.country.isin(["Saudi Arabia", "United Arab Emirates",
                                                     "Qatar", "Kuwait"]))]
    world = shares(f, "rev")
    rmax = 40  # one shared scale; the few spokes above it are clipped and labelled
    fig = plt.figure(figsize=(12, 11))
    for i, (name, mask) in enumerate(groups):
        r, col = divmod(i, 3)
        ax = fig.add_axes([0.05 + col * 0.33, 0.49 - r * 0.45, 0.24, 0.3], polar=True)
        x = f[mask]
        own = shares(x, "rev")
        spider(ax, [(world, MUTED, "World mix", False),
                    ([min(v, rmax) for v in own], BAR, name, True)], rmax=rmax)
        for j, v in enumerate(own):
            if v > rmax:
                ax.annotate(f"{v:.0f}% (off scale)", xy=(j / len(AXES) * 2 * math.pi, rmax),
                            xytext=(0, 6), textcoords="offset points", ha="center",
                            fontsize=10, fontweight="bold", color=BAR)
        ax.set_title(f"{name}\n{len(x)} firms · ${x.rev.sum() / 1e6:,.1f}T revenue",
                     fontsize=11, fontweight="bold", color=INK, pad=34)
    fig.text(0.02, 0.985, "Every economy has its own business DNA", fontsize=18,
             fontweight="bold", color=INK, va="top")
    fig.text(0.02, 0.95, "Share of each country's Global 2000 revenue by kind of business (blue), "
             "against the world mix (grey dashed)", fontsize=11.5, color="#4A5563", va="top")
    fig.text(0.02, 0.005, f"Source: Forbes Global 2000 ({YEAR}). Same 0–40% scale on every chart; spokes beyond it are labelled. "
             "Forbes files carmakers under Consumer & Retail.", fontsize=8.5, color=MUTED)
    fig.savefig(IMG_OUT / "10_idea_fingerprint_countries.png")
    plt.close(fig)
    print("wrote 10_idea_fingerprint_countries.png")


if __name__ == "__main__":
    comp = load()
    comp.drop(columns=["description"]).to_csv(DATA_OUT / "business_ideas.csv", index=False)
    print("wrote business_ideas.csv", len(comp), "companies;",
          (comp.what_they_do != "").sum(), "with a one-line idea")
    sec = sector_table(comp)
    sec.to_csv(DATA_OUT / "idea_sectors.csv", index=False)
    pd.set_option("display.width", 250)
    print(sec.drop(columns=["the_idea"]).round(3).to_string(index=False))
    forbes = comp[comp.list.str.startswith("Forbes Global")]
    chart_world(forbes)
    chart_countries(forbes)
