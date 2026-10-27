"""Build the private-company / startup dataset from Forbes Cloud 100 and
Next Billion-Dollar Startups, plus a valuation chart.

Usage: python scripts/build_startups.py [year] [rawdir]   (default 2026, data/raw_2026)
A list with no JSON for that year (no edition yet) is skipped with a message.
Writes data/startups_<year>.csv; chart/findings only overwritten for 2025."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
_RD = Path(sys.argv[2] if len(sys.argv) > 2 else f"data/raw_{YEAR}")
RAW = {
    "Cloud 100": _RD / f"cloud100_{YEAR}_api.json",
    "Next Billion-Dollar Startups": _RD / f"nextbillion_{YEAR}_api.json",
}
OUT_CSV = Path(f"data/startups_{YEAR}.csv")
OUT_DIR = Path("output/charts")
OUT_DIR.mkdir(parents=True, exist_ok=True)

INK, BAR, ACCENT, MUTED, BG = "#0B2545", "#1B6CA8", "#E07A4F", "#9AA5B1", "#FFFFFF"


def main() -> None:
    rows = []
    for list_name, path in RAW.items():
        if not path.exists():
            print(f"{list_name} {YEAR}: no edition/JSON ({path}) - skipped")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        orgs = data["organizationList"]["organizationsLists"]
        for r in orgs:
            rows.append({
                "list": list_name,
                "rank": r.get("rank") or r.get("position"),
                "company": r.get("organizationName") or r.get("name"),
                "uri": r.get("uri"),
                "country": r.get("country"),
                "industry": (r.get("industry") or r.get("shortDescription") or "").strip() or None,
                "city": r.get("city"),
                "state": r.get("state"),
                "ceo": r.get("ceoName"),
                "ceo_title": r.get("ceoTitle"),
                "year_founded": r.get("yearFounded"),
                "website": r.get("webSite"),
                # Forbes reports Cloud 100 valuation and funding in USD millions
                "valuation_musd": r.get("marketValue"),
                "funding_musd": r.get("funding"),
                "employees": r.get("employees"),
                "description": (r.get("description") or "").strip() or None,
            })

    df = pd.DataFrame(rows)
    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"wrote {OUT_CSV}  shape={df.shape}")

    cloud = df[df["list"] == "Cloud 100"].dropna(subset=["valuation_musd"])
    if YEAR != 2025 or cloud.empty:
        print("skipping chart/findings (2025 legacy outputs only)")
        return
    print(f"Cloud 100 valuations: {len(cloud)}, total ${cloud['valuation_musd'].sum()/1e6:,.2f}T")

    # ---- chart: top 15 Cloud 100 by valuation ----
    top = cloud.nlargest(15, "valuation_musd").sort_values("valuation_musd")
    labels = top["company"].tolist()
    values = (top["valuation_musd"] / 1000).tolist()  # billions

    plt.rcParams.update({
        "font.family": "Segoe UI", "figure.facecolor": BG, "axes.facecolor": BG,
        "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK,
        "xtick.color": INK, "ytick.color": INK, "savefig.dpi": 200, "figure.dpi": 200,
    })
    fig, ax = plt.subplots(figsize=(9, 6))
    y = np.arange(len(labels))
    ax.barh(y, values, color=[ACCENT if v == max(values) else BAR for v in values], height=0.68)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.grid(axis="x", color="#E4E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    for yi, v in zip(y, values):
        ax.text(v + max(values) * 0.012, yi, f"${v:,.0f}B", va="center", fontsize=8.5)
    ax.set_xlim(0, max(values) * 1.18)
    ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}B"))
    ax.set_title("The private half-trillion club", loc="left", fontsize=15,
                 fontweight="bold", pad=18)
    ax.text(0, 1.02, "Forbes Cloud 100, 2025 — top 15 by valuation (USD billions)",
            transform=ax.transAxes, fontsize=10, color="#4A5568", va="bottom")
    fig.text(0, -0.02, "Source: Forbes Cloud 100 (2025)", fontsize=8, color=MUTED)
    fig.savefig(OUT_DIR / "08_startup_valuations.png", bbox_inches="tight")
    plt.close(fig)
    print("wrote chart 08")

    # ---- findings ----
    lines = ["# Startups (Forbes 2025 lists)\n"]
    lines.append(f"- Cloud 100: {len(cloud)} companies with a valuation, "
                 f"combined **${cloud['valuation_musd'].sum()/1e6:,.2f}T**")
    lines.append(f"- Median Cloud 100 valuation: **${cloud['valuation_musd'].median()/1000:,.1f}B**")
    lines.append(f"- Next Billion-Dollar Startups: {len(df[df['list'] != 'Cloud 100'])} companies")
    by_c = cloud["country"].value_counts().head(8)
    lines.append("\nCloud 100 by country: " + ", ".join(f"{k} ({v})" for k, v in by_c.items()))
    by_i = cloud["industry"].value_counts().head(8)
    lines.append("\nCloud 100 by industry: " + "; ".join(f"{k} ({v})" for k, v in by_i.items()))
    Path("analysis/startups_findings.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
