"""Build the study pack: tables, charts and one readable document.

The analysis engine (``analysis/*``) produces metrics and tables.  This script
is the orchestrator that turns those into the deliverable a writer can work
from:

* ``output/data/<module>__<table>.csv`` - every table the engine produced
* ``output/metrics.json``               - every metric plus its insight lines
* ``output/charts/NN_<slug>.png``       - every chart, house style
* ``output/STUDY_PACK.md``              - the study pack as Markdown
* ``output/study_pack.html``            - the same pack as a self-contained page
* ``output/README.md``                  - index of the above

It deliberately writes **no article prose**.  The pack states what the data
shows; the article is written separately.

Run::

    python data_analysis/build_report.py
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Any, Callable

PKG = Path(__file__).resolve().parent
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))

import numpy as np
import pandas as pd

import analysis
import config
import context as ctxmod
import doc
import report_charts
from report_charts import ChartBook
from style import money_b, money_m

# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #


def mv(metrics: dict, *path: str, default: Any = "—") -> Any:
    """Walk a nested dict with a string path, e.g. mv(m, "cohort_revenue", "cagr_pct")."""
    cur: Any = metrics
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


def usd(v: Any) -> str:
    """Format a value in raw US dollars."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return money_b(float(v) / 1e9)


def usdm(v: Any) -> str:
    """Format a value in raw US dollars, expressed in millions."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return money_m(float(v) / 1e6)


def pct(v: Any) -> str:
    """Format a percentage that may be stored as a fraction (0-1) or a percent."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    x = float(v)
    if abs(x) <= 1.5:
        x *= 100.0
    return f"{x:,.1f}%"


def ratio(v: Any, suffix: str = "x") -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return f"{float(v):,.2f}{suffix}"


def num(v: Any, digits: int = 0) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return f"{float(v):,.{digits}f}"


def count(v: Any) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return f"{int(round(float(v))):,}"


# -- column-aware cell formatting ------------------------------------------- #
_USD_B = {
    "revenue_usd", "profit_usd", "assets_usd", "market_cap_usd",
    "valuation_usd", "gdp_usd", "total", "total_rev", "total_prof",
    "revenue", "profit", "market_cap", "equity_value",
}
_USD_M = {
    "revenue_musd", "profit_musd", "market_cap_musd", "revenue_musd",
    "valuation_musd",
}
_PCT = {
    "revenue_share", "profit_share", "market_cap_share", "profit_margin",
    "loss_rate", "revenue_pct", "profit_pct",
}
_RATIO = {
    "index_vs_gdp", "mcap_to_gdp", "market_cap_to_revenue",
    "market_cap_to_profit", "revenue_per_gdp",
}


def fmt_cell(col: str, v: Any) -> str:
    """Format one table cell based on its column name."""
    if v is None:
        return "—"
    if isinstance(v, (bool, np.bool_)):
        return "yes" if v else "no"
    if isinstance(v, str):
        return v
    if isinstance(v, (int, np.integer)):
        v = float(v)
    if isinstance(v, (float, np.floating)):
        if np.isnan(v):
            return "—"
        c = col.lower()
        if c in _USD_B:
            return usd(v)
        if c in _USD_M:
            return usdm(v)
        if c in _PCT or c.endswith("_pct") or c.endswith("_percent"):
            return pct(v)
        if c in _RATIO:
            return ratio(v)
        if c in {"companies", "firms", "n", "rows", "count", "employees",
                 "year", "rank", "forbes_rank", "rank_now", "rank_start",
                 "companies_count", "countries"}:
            return count(v)
        if abs(v) >= 1000:
            return count(v)
        if abs(v) < 1:
            return f"{v:,.3f}"
        return f"{v:,.2f}"
    return str(v)


def build_table(df: pd.DataFrame, columns: list[str] | None = None,
                max_rows: int = 20) -> tuple[list[str], list[list[str]]]:
    """Turn a DataFrame into formatted column names and rows."""
    if df is None or len(df) == 0:
        return [], []
    cols = list(df.columns)
    if columns:
        keep = [c for c in columns if c in cols]
        if keep:
            cols = keep
    head = [str(c) for c in cols]
    rows: list[list[str]] = []
    for _, rec in df.head(max_rows).iterrows():
        rows.append([fmt_cell(str(c), rec[c]) for c in cols])
    return head, rows


# --------------------------------------------------------------------------- #
# engine
# --------------------------------------------------------------------------- #


def run_modules(ctx) -> tuple[dict[str, dict], list[str]]:
    """Run every analysis module and collect metrics, tables and insights."""
    results: dict[str, dict] = {}
    problems: list[str] = []
    for mod in analysis.MODULES:
        try:
            res = mod.run(ctx)
        except Exception as exc:                      # pragma: no cover
            problems.append(f"{mod.KEY}: run() failed -> {exc}")
            continue
        try:
            res["insights"] = list(mod.insights(res["metrics"]))
        except Exception as exc:
            problems.append(f"{mod.KEY}: insights() failed -> {exc}")
            res["insights"] = []
        results[mod.KEY] = res
        print(f"  module {mod.KEY:<16} metrics={len(res['metrics']):>3} "
              f"tables={len(res.get('tables') or {}):>2} "
              f"insights={len(res['insights']):>2}")
    return results, problems


def write_tables(results: dict[str, dict]) -> list[dict]:
    """Write every table the engine produced to output/data/."""
    out_dir = config.OUT_DATA
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[dict] = []
    for key, res in results.items():
        for name, df in (res.get("tables") or {}).items():
            if not isinstance(df, pd.DataFrame) or df.empty:
                continue
            fname = f"{key}__{name}.csv"
            path = out_dir / fname
            try:
                df.to_csv(path, index=False)
            except Exception as exc:                  # pragma: no cover
                print(f"  !! could not write {fname}: {exc}")
                continue
            written.append({
                "file": f"data/{fname}",
                "module": key,
                "table": name,
                "rows": int(len(df)),
                "columns": [str(c) for c in df.columns],
            })
    return written


def json_default(o: Any) -> Any:
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, pd.DataFrame):
        return o.to_dict("records")
    if isinstance(o, pd.Series):
        return o.to_dict()
    if isinstance(o, (set, tuple)):
        return list(o)
    if isinstance(o, (pd.Timestamp, date)):
        return str(o)
    return str(o)


def write_metrics_json(results: dict[str, dict]) -> Path:
    payload = {
        key: {
            "metrics": res["metrics"],
            "insights": res.get("insights", []),
            "tables": sorted((res.get("tables") or {}).keys()),
        }
        for key, res in results.items()
    }
    path = config.OUT / "metrics.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=json_default,
                               ensure_ascii=False), encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# charts
# --------------------------------------------------------------------------- #
_CHART_FUNCS = {
    "scale": report_charts.charts_scale,
    "geography": report_charts.charts_geography,
    "industry": report_charts.charts_industry,
    "ownership": report_charts.charts_ownership,
    "capital": report_charts.charts_capital,
    "private_capital": report_charts.charts_private,
    "time_series": report_charts.charts_time,
    "data_quality": report_charts.charts_quality,
    "companies": report_charts.charts_companies,
}


def build_charts(ctx, results: dict[str, dict]) -> ChartBook:
    """Draw every chart. A chart that fails is reported, not fatal."""
    book = ChartBook(config.OUT_CHARTS)
    for key, fn in _CHART_FUNCS.items():
        res = results.get(key)
        if res is None:
            continue
        try:
            book.current_module = key
            fn(book, ctx, res)
        except Exception as exc:                      # pragma: no cover
            book.failures.append({"chart": f"{key} (module level)", "error": str(exc)})
    book.current_module = None
    return book


# --------------------------------------------------------------------------- #
# study pack
# --------------------------------------------------------------------------- #

# Each section: module key, heading, one-line lead, the tables to show and
# the key numbers to put at the top of the section.
SECTIONS: list[dict] = [
    {
        "key": "scale",
        "title": "Scale: the size of the measured corporate world",
        "lead": "How much revenue, profit, assets and workforce the reconciled "
                "universe of large firms actually represents, and how steeply "
                "that value is concentrated.",
        "kv": [
            ("Forbes Global 2000 firms", lambda m: count(m.get("forbes_company_count"))),
            ("Combined revenue", lambda m: usd(m.get("forbes_revenue_total"))),
            ("Combined profit", lambda m: usd(m.get("forbes_profit_total"))),
            ("Combined assets", lambda m: usd(m.get("forbes_assets_total"))),
            ("Combined market value", lambda m: usd(m.get("forbes_market_cap_total"))),
            ("Employees", lambda m: count(m.get("forbes_employees_total"))),
            ("Blended net margin", lambda m: pct(m.get("forbes_blended_margin"))),
            ("Firms that lose money", lambda m: count(m.get("forbes_loss_makers"))),
        ],
        "tables": [
            ("thresholds", "Firm counts above each revenue threshold", None, 14),
            ("top_beyond_forbes",
             "Largest firms that are not on Forbes' Global 2000 list",
             ["company", "country", "revenue_musd", "sector"], 15),
        ],
    },
    {
        "key": "geography",
        "title": "Geography: where the money sits",
        "lead": "How the measured corporate revenue and profit distribute across "
                "countries and regions, and how far that map deviates from a map "
                "of world GDP.",
        "tables": [
            ("regions_mixed", "Regional rollup of the reconciled universe", None, 12),
            ("country_mixed",
             "Largest country economies of the corporate world",
             ["country", "companies", "revenue_usd", "profit_usd",
              "market_cap_usd", "revenue_share", "index_vs_gdp"], 20),
            ("over_under",
             "Countries over- and under-indexed against their own GDP",
             ["country", "companies", "revenue_usd", "gdp_usd",
              "revenue_share", "gdp_share", "index_vs_gdp"], 20),
        ],
    },
    {
        "key": "industry",
        "title": "Industry: what the money does",
        "lead": "Which sectors carry the revenue, which carry the profit, and "
                "how wide the margin distributions are inside each sector.",
        "tables": [
            ("sectors", "Sector scoreboard", None, 20),
            ("margin_dispersion",
             "Spread of net margins inside each sector", None, 20),
            ("sector_concentration",
             "How concentrated each sector is", None, 20),
        ],
    },
    {
        "key": "ownership",
        "title": "Ownership: who owns it",
        "lead": "State, listed, private, mutual and subsidiary capital, and the "
                "large firms that no ranking list puts on the page.",
        "tables": [
            ("ownership_mixed",
             "Ownership split of the reconciled universe", None, 12),
            ("true_top100",
             "The true top 100 once every source is reconciled",
             ["company", "country", "ownership", "sector",
              "revenue_usd", "forbes_rank"], 25),
            ("invisible_by_country",
             "The invisible giants, by country", None, 15),
        ],
    },
    {
        "key": "capital",
        "title": "Capital: what the markets think it is worth",
        "lead": "The listed universe: market value, sector multiples, the gap "
                "between where profit sits and where valuation sits, and how "
                "deep each national equity market is against its GDP.",
        "tables": [
            ("profit_pool",
             "Profit share against market-value share, by sector", None, 20),
            ("financial_depth",
             "Equity-market depth against GDP", None, 20),
            ("top_listed",
             "Largest listed companies by market value", None, 20),
            ("exchanges", "Exchanges by total market capitalisation", None, 20),
        ],
    },
    {
        "key": "private_capital",
        "title": "Private capital: the part without a ticker",
        "lead": "The private half of the economy: unicorn valuations, the "
                "largest unlisted operating companies, and the frontier-lab "
                "landscape.",
        "tables": [
            ("unicorns_by_country", "Unicorns by country", None, 15),
            ("unicorns_by_industry", "Unicorns by industry", None, 15),
            ("unlisted_top",
             "Largest unlisted companies by revenue", None, 20),
        ],
    },
    {
        "key": "time_series",
        "title": "Time series: how the picture changed",
        "lead": "The tracked cohort across years: revenue and profit paths, "
                "where the profit pool moved, and which firms climbed.",
        "tables": [
            ("cohort_revenue_series",
             "Cohort revenue, year by year", None, 30),
            ("cohort_margin_path", "Cohort margin path", None, 30),
            ("profit_pool_migration",
             "Change in profit share by industry", None, 20),
            ("mobility_forbes",
             "Fastest risers among the ranked firms", None, 20),
        ],
    },
    {
        "key": "data_quality",
        "title": "Data quality: how far to trust the above",
        "lead": "Where fields are empty, where two sources disagree, how old "
                "each dataset is, and the caveats that apply to every number "
                "in this pack.",
        "tables": [
            ("missingness_key",
             "Where the data actually is missing", None, 25),
            ("cross_source_disagreement",
             "How the sources disagree about the same company", None, 15),
            ("data_vintages", "Vintage of every source", None, 30),
        ],
    },
    {
        "key": "companies",
        "title": "Companies: one page for every firm",
        "lead": "The directory behind the aggregates. Every company the "
                "reconciliation could name, with whatever is actually known "
                "about each one: size, sector, owner, country, and a way "
                "through to the company itself.",
        "kv": [
            ("Companies in the directory", lambda m: count(m.get("companies"))),
            ("With an official website", lambda m: count(m.get("with_website"))),
            ("With a Wikipedia page", lambda m: count(m.get("with_wikipedia"))),
            ("With a one-line description", lambda m: count(m.get("with_description"))),
            ("With a revenue figure", lambda m: count(m.get("with_revenue"))),
            ("With a market value", lambda m: count(m.get("with_market_cap"))),
        ],
        "tables": [
            ("company_directory",
             "The largest companies in the directory",
             ["company", "country", "sector", "ownership", "revenue_usd",
              "market_cap_usd"], 25),
        ],
    },
]


#: Which table holds the numbers behind each chart, so the web app can show
#: the reader the data a chart is drawn from.  Charts without an entry simply
#: have no data panel.
CHART_TABLES = {
    "top20_revenue": "top20",
    "revenue_thresholds": "thresholds",
    "rank_size_zipf": "rank_size",
    "truncation_gap": "top_beyond_forbes",
    "top_countries": "country_mixed",
    "revenue_vs_gdp": "over_under",
    "regions": "regions_mixed",
    "region_compare": "regions_forbes",
    "sector_revenue_profit": "sectors",
    "sector_margin": "sectors",
    "margin_dispersion": "margin_dispersion",
    "roa_decomposition": "sectors",
    "sector_concentration": "sector_concentration",
    "ownership_mix": "ownership_mixed",
    "invisible_giants": "invisible_by_country",
    "true_top100": "true_top100",
    "margin_by_ownership": "margin_tests",
    "top_listed": "top_listed",
    "multiples_by_sector": "multiples_by_sector",
    "profit_vs_mcap": "profit_pool",
    "financial_depth": "financial_depth",
    "exchanges": "exchanges",
    "unicorns_country": "unicorns_by_country",
    "unicorns_industry": "unicorns_by_industry",
    "unicorn_wave": "unicorns_by_year",
    "unlisted_top": "unlisted_top",
    "ai_modality": "ai_by_modality",
    "cohort_revenue": "cohort_revenue_series",
    "cohort_margin": "cohort_margin_path",
    "rank_mobility": "mobility_forbes",
    "profit_pool_migration": "profit_pool_migration",
    "missingness": "missingness_key",
    "confidence": "confidence",
    "cross_source": "cross_source_disagreement",
    "every_company_we_can_measure": "company_presence",
    "every_company_the_market_can_see": "company_presence",
}

#: Captions for the tables a section already lists, reused by the chart
#: data panels.
_TABLE_CAPTIONS = {
    (spec["key"], tkey): caption
    for spec in SECTIONS
    for tkey, caption, _cols, _n in spec.get("tables", [])
}


def _section_kv(spec: dict, metrics: dict) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for label, fn in spec.get("kv", []):
        try:
            out.append((label, fn(metrics)))
        except Exception:
            out.append((label, "—"))
    return out


def _country_count(ctx) -> str:
    """Countries that actually have a measured firm (not the size of the index)."""
    if "country_iso3" in ctx.reconciled.columns:
        return count(ctx.reconciled["country_iso3"].nunique())
    if "iso3" in ctx.idx.columns:
        return count(ctx.idx["iso3"].nunique())
    return count(len(ctx.idx))


def build_study_pack(ctx, results: dict[str, dict], book: ChartBook,
                      tables_written: list[dict]) -> tuple[doc.Doc, list[tuple[str, str]]]:
    """Assemble the study pack document."""
    d = doc.Doc("The Business World in Numbers — Study Pack")
    toc: list[tuple[str, str]] = []

    # -- front matter ------------------------------------------------------- #
    d.h1("How to use this pack")
    d.p(
        "This is the analysis layer of the project: the measurements, the "
        "tables, the charts and the caveats. It is written so that it can be "
        "read as a reference and quoted from, and it deliberately contains no "
        "article prose. Every figure below is reproduced from the datasets "
        "listed in the appendix and can be regenerated with "
        "`python data_analysis/build_report.py`."
    )
    d.note(
        "**Reading the numbers.** Revenue, profit, assets and market value are "
        "converted to US dollars. Market value is a point-in-time measure and "
        "is not additive with revenue; the two live on separate ledgers. "
        "Country is the domicile of the company, not the nationality of its "
        "owners, and several of the largest firms are domiciled in places that "
        "have no large domestic economy of their own."
    )

    d.h2("The universe at a glance")
    scale = results.get("scale", {}).get("metrics", {})
    listed = results.get("capital", {}).get("metrics", {})
    private = results.get("private_capital", {}).get("metrics", {})
    uni = private.get("unicorns", {}) if isinstance(private.get("unicorns"), dict) else {}
    d.kv([
        ("Firms in the Forbes Global 2000",
         count(scale.get("forbes_company_count"))),
        ("Firms in the reconciled universe",
         count(len(ctx.reconciled))),
        ("Rows before reconciliation", count(len(ctx.universe))),
        ("Rows where sources disagreed", count(len(ctx.conflicts))),
        ("Listed companies with a market value",
         count(mv(listed, "listed", "companies"))),
        ("Listed companies' market value",
         usd(mv(listed, "listed", "total_market_cap"))),
        ("Private unicorns tracked", count(uni.get("count"))),
        ("Unicorn paper valuation", usd(uni.get("total_valuation"))),
        ("Countries with at least one measured firm", _country_count(ctx)),
    ])
    d.note(
        "**Three ledgers, not one.** The Forbes list measures *revenue*. The "
        "listed universe measures *market value*. The unicorn board measures "
        "*private paper valuation*. They cover different companies and "
        "different years, so they must never be added together or compared "
        "as shares of a single pie."
    )

    # -- one section per module --------------------------------------------- #
    for spec in SECTIONS:
        key = spec["key"]
        res = results.get(key)
        if res is None:
            continue
        metrics = res["metrics"]
        tables = res.get("tables") or {}

        d.h1(spec["title"])
        toc.append((spec["title"], f"sec-{doc._slug(spec['title'])}"))
        d.p(spec["lead"])

        kv = _section_kv(spec, metrics)
        if kv:
            d.h3("Key numbers")
            d.kv(kv)

        insights = res.get("insights") or []
        if insights:
            d.h3("What the data shows")
            d.bullets(insights)

        # charts belonging to this module
        charts = [c for c in book.records if c.get("module") == key]
        if charts:
            d.h3("Charts")
            for c in charts:
                d.image(c["path"], c["caption"])

        # tables
        for tkey, caption, columns, max_rows in spec.get("tables", []):
            df = tables.get(tkey)
            if not isinstance(df, pd.DataFrame) or df.empty:
                continue
            head, rows = build_table(df, columns, max_rows)
            if not head or not rows:
                continue
            d.h3(caption)
            d.table(head, rows, caption)
            d.p(f"_Full table: `data/{key}__{tkey}.csv`_ "
                f"({len(df):,} rows, {len(df.columns)} columns)._")

    # -- appendix ----------------------------------------------------------- #
    d.h1("Appendix A: the datasets behind every number")
    d.p("Each row is one source file, what it measures, who publishes it and "
        "how much weight it was given.")
    reg_rows = []
    for ds in config.REGISTRY:
        reg_rows.append([
            str(ds.label), str(ds.kind), str(ds.trust),
            str(ds.publisher or "—"),
            str(ds.path.name if hasattr(ds.path, "name") else ds.path),
            str(ds.notes or "—"),
        ])
    d.table(["Dataset", "Kind", "Trust", "Publisher", "File", "Notes"],
            reg_rows, "Dataset registry")

    d.h1("Appendix B: chart index")
    d.p("Every chart is written to `charts/` next to this document.")
    chart_rows = [[c["id"], c["title"], c["subtitle"], f"charts/{c['file']}"]
                  for c in book.records]
    if chart_rows:
        d.table(["#", "Title", "Subtitle", "File"], chart_rows, "Charts")
    if book.failures:
        d.note("**Charts that could not be drawn:** " + "; ".join(
            f"{f['chart']} ({f['error']})" for f in book.failures))

    d.h1("Appendix C: table index")
    d.p("Every table the engine produced, written as CSV.")
    tbl_rows = [[t["module"], t["table"], f"{t['rows']:,}",
                 ", ".join(t["columns"][:10]) + ("..." if len(t["columns"]) > 10 else ""),
                 f"data/{t['module']}__{t['table']}.csv"]
                for t in tables_written]
    if tbl_rows:
        d.table(["Module", "Table", "Rows", "Columns", "File"], tbl_rows, "Tables")

    d.h1("Appendix D: caveats")
    caveats = results.get("data_quality", {}).get("metrics", {}).get("caveats") or []
    if caveats:
        d.bullets([str(c) for c in caveats])
    else:
        d.bullets([
            "Market value is a snapshot; it changes daily and is not "
            "comparable across the years in the history file.",
            "Revenue and profit come from company filings and from Forbes' own "
            "compilation, which mix fiscal years and accounting standards.",
            "Private-company valuations are negotiated prices reported by "
            "funding rounds, not appraisals.",
        ])
    d.p("Generated by `data_analysis/build_report.py`.")
    return d, toc


def write_outputs(d: doc.Doc, book: ChartBook, tables_written: list[dict],
                  problems: list[str]) -> None:
    out = config.OUT
    out.mkdir(parents=True, exist_ok=True)

    md = out / "STUDY_PACK.md"
    md.write_text(d.to_markdown(), encoding="utf-8")

    html = out / "study_pack.html"
    toc = _toc_for(d)
    html.write_text(d.to_html(
        subtitle="A data study of the large-company world: scale, geography, "
                 "industry, ownership, capital, private markets, change over "
                 "time, and the quality of the underlying data.",
        toc=toc), encoding="utf-8")

    readme = out / "README.md"
    lines = [
        "# Study pack output",
        "",
        "Everything here is regenerated by:",
        "",
        "```",
        "python data_analysis/build_report.py",
        "```",
        "",
        "| File | What it is |",
        "|---|---|",
        "| `index.html` | **The browsable app** - open this in a browser to "
        "study the whole pack with the charts inline. |",
        "| `companies.js` | The company directory behind the app: every "
        "company in the universe with its website and links. |",
        "| `STUDY_PACK.md` | The study pack as Markdown - the main deliverable. |",
        "| `study_pack.html` | The same pack as a single self-contained page "
        "with the charts inline. |",
        "| `metrics.json` | Every metric and insight line, machine readable. |",
        f"| `charts/` | {len(book.records)} charts, house style. |",
        f"| `data/` | {len(tables_written)} tables as CSV. |",
        "",
        "## Charts",
        "",
    ]
    for c in book.records:
        lines.append(f"- `{c['path']}` - {c['title']} ({c['subtitle']})")
    if book.failures:
        lines += ["", "### Charts that failed", ""]
        for f in book.failures:
            lines.append(f"- **{f['chart']}**: {f['error']}")
    if problems:
        lines += ["", "### Module problems", ""]
        for p in problems:
            lines.append(f"- {p}")
    lines.append("")
    readme.write_text("\n".join(lines), encoding="utf-8")


def _toc_for(d: doc.Doc) -> list[tuple[str, str]]:
    """Collect the h1 headings of the document as a table of contents."""
    toc: list[tuple[str, str]] = []
    for kind, payload in d.blocks:
        if kind == "h1":
            toc.append((str(payload), f"sec-{doc._slug(payload)}"))
    return toc


# --------------------------------------------------------------------------- #
# web app
# --------------------------------------------------------------------------- #
# A small browsable site so the pack can be studied without opening the
# Markdown.  The shell (index.html, styles.css, app.js) lives in
# ``data_analysis/app`` and is copied next to the charts and the data, so the
# whole deliverable is one folder that opens from the file system.

APP_SRC = config.PKG / "app"
APP_FILES = ("index.html", "styles.css", "app.js")

WEB_SUBTITLE = (
    "A browsable study of the large-company world: how big it is, where it "
    "sits, what it does, who owns it, what the markets think it is worth, "
    "the private half with no ticker, how the picture changed, and how far "
    "to trust the underlying data."
)

WEB_NOTE = (
    "Three ledgers, not one. The Forbes list measures revenue. The listed "
    "universe measures market value. The unicorn board measures private "
    "paper valuation. They cover different companies and different years, "
    "so they must never be added together or compared as shares of a "
    "single pie. Market value is a point-in-time measure and is not "
    "additive with revenue; country is the domicile of the company, not "
    "the nationality of its owners."
)


def _web_universe(ctx, results: dict[str, dict]) -> list[dict]:
    """The 'universe at a glance' numbers, as label/value pairs."""
    scale = results.get("scale", {}).get("metrics", {})
    listed = results.get("capital", {}).get("metrics", {})
    private = results.get("private_capital", {}).get("metrics", {})
    uni = private.get("unicorns", {}) if isinstance(private.get("unicorns"), dict) else {}
    pairs = [
        ("Forbes Global 2000 firms", count(scale.get("forbes_company_count"))),
        ("Firms in the reconciled universe", count(len(ctx.reconciled))),
        ("Rows before reconciliation", count(len(ctx.universe))),
        ("Rows where sources disagreed", count(len(ctx.conflicts))),
        ("Listed companies", count(mv(listed, "listed", "companies"))),
        ("Listed market value", usd(mv(listed, "listed", "total_market_cap"))),
        ("Private unicorns tracked", count(uni.get("count"))),
        ("Unicorn paper valuation", usd(uni.get("total_valuation"))),
        ("Countries with a measured firm", _country_count(ctx)),
    ]
    return [{"label": label, "value": value} for label, value in pairs]


def _chart_data(module_key: str, chart_id: str, tables: dict) -> dict | None:
    """The table a chart is drawn from, formatted for the app."""
    tkey = CHART_TABLES.get(chart_id)
    if not tkey:
        return None
    df = tables.get(tkey)
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None
    head, rows = build_table(df, None, min(len(df), 60))
    if not head or not rows:
        return None
    caption = _TABLE_CAPTIONS.get((module_key, tkey), "The numbers behind this chart")
    return {
        "title": caption,
        "columns": head,
        "rows": rows,
        "csv": f"data/{module_key}__{tkey}.csv",
        "total_rows": int(len(df)),
    }


def _web_sections(results: dict[str, dict], book: ChartBook) -> list[dict]:
    """One payload entry per analysis module: numbers, insights, charts, tables."""
    out: list[dict] = []
    for spec in SECTIONS:
        key = spec["key"]
        res = results.get(key)
        if res is None:
            continue
        tables = res.get("tables") or {}

        charts = []
        for c in book.records:
            if c.get("module") != key:
                continue
            charts.append({
                "id": c["id"],
                "title": c["title"],
                "subtitle": c["subtitle"],
                "src": c["path"],
                "caption": c["caption"],
                # ``slug`` is the stable name of the chart; ``id`` is only its
                # position in the book, and CHART_TABLES is keyed by slug.
                "data": _chart_data(key, c.get("slug") or c["id"], tables),
            })

        table_specs = []
        for tkey, caption, columns, max_rows in spec.get("tables", []):
            df = tables.get(tkey)
            if not isinstance(df, pd.DataFrame) or df.empty:
                continue
            head, rows = build_table(df, columns, min(len(df), 200))
            if not head or not rows:
                continue
            table_specs.append({
                "title": caption,
                "columns": head,
                "rows": rows,
                "csv": f"data/{key}__{tkey}.csv",
                "total_rows": int(len(df)),
            })

        out.append({
            "id": f"sec-{doc._slug(spec['title'])}",
            "key": key,
            "title": spec["title"],
            "lead": spec["lead"],
            "kv": [{"label": a, "value": b}
                   for a, b in _section_kv(spec, res["metrics"])],
            "insights": list(res.get("insights") or []),
            "charts": charts,
            "tables": table_specs,
        })
    return out


def _web_appendix(results: dict[str, dict], book: ChartBook,
                   tables_written: list[dict]) -> dict:
    """Dataset registry, chart index, table index and caveats."""
    ds_rows = [[str(ds.label), str(ds.kind), str(ds.trust),
                str(ds.publisher or "—"),
                str(ds.path.name if hasattr(ds.path, "name") else ds.path),
                str(ds.notes or "—")]
               for ds in config.REGISTRY]
    chart_rows = [[c["id"], c["title"], c["subtitle"], c["path"]]
                  for c in book.records]
    table_rows = [[t["module"], t["table"], f"{t['rows']:,}",
                   ", ".join(t["columns"][:10]) +
                   ("..." if len(t["columns"]) > 10 else ""),
                   f"data/{t['module']}__{t['table']}.csv"]
                  for t in tables_written]

    caveats = results.get("data_quality", {}).get("metrics", {}).get("caveats") or []
    if not caveats:
        caveats = [
            "Market value is a snapshot; it changes daily and is not "
            "comparable across the years in the history file.",
            "Revenue and profit come from company filings and from Forbes' own "
            "compilation, which mix fiscal years and accounting standards.",
            "Private-company valuations are negotiated prices reported by "
            "funding rounds, not appraisals.",
        ]

    return {
        "datasets": {
            "columns": ["Dataset", "Kind", "Trust", "Publisher", "File", "Notes"],
            "rows": ds_rows,
        },
        "charts": {
            "columns": ["#", "Title", "Subtitle", "File"],
            "rows": chart_rows,
        },
        "tables": {
            "columns": ["Module", "Table", "Rows", "Columns", "File"],
            "rows": table_rows,
        },
        "caveats": [str(c) for c in caveats],
    }


def _web_companies(results: dict[str, dict]) -> dict:
    """The company directory as a compact, column-oriented payload.

    One file holds every company, so the app can search it without a server
    round-trip.  Columns rather than objects keeps the file small, and empty
    fields are dropped rather than written out as nulls.
    """
    res = results.get("companies", {})
    df = res.get("tables", {}).get("company_directory")
    if not isinstance(df, pd.DataFrame) or df.empty:
        return {"columns": [], "rows": []}
    if "description" in df.columns:
        df = df.assign(description=df["description"].astype(str).str.slice(0, 240))
    columns = list(df.columns)
    data: dict[str, list] = {}
    for c in columns:
        series = df[c]
        if series.dtype.kind in "if":
            data[c] = [None if pd.isna(v) else float(v) for v in series]
        else:
            data[c] = ["" if (v is None or (isinstance(v, float) and pd.isna(v)))
                           else str(v) for v in series]
    rows = [list(r) for r in zip(*[data[c] for c in columns])]
    return {"columns": columns, "rows": rows}


def write_web_app(ctx, results: dict[str, dict], book: ChartBook,
                  tables_written: list[dict]) -> Path:
    """Write the browsable app: index.html, styles.css, app.js, data.js,
    companies.js."""
    payload = {
        "title": "The Business World in Numbers",
        "eyebrow": "A data study of the large-company world",
        "subtitle": WEB_SUBTITLE,
        "generated": date.today().isoformat(),
        "note": WEB_NOTE,
        "universe": _web_universe(ctx, results),
        "sections": _web_sections(results, book),
        "appendix": _web_appendix(results, book, tables_written),
        "chart_count": len(book.records),
        "table_count": len(tables_written),
    }
    out = config.OUT
    out.mkdir(parents=True, exist_ok=True)
    js = ("/* generated by build_report.py - do not edit */\n"
          "window.STUDY_PACK = " +
          json.dumps(payload, indent=1, default=json_default,
                     ensure_ascii=False) + ";\n")
    (out / "data.js").write_text(js, encoding="utf-8")

    companies = _web_companies(results)
    cjs = ("/* generated by build_report.py - do not edit */\n"
           "window.COMPANIES = " +
           json.dumps(companies, default=json_default, ensure_ascii=False,
                      separators=(",", ":")) + ";\n")
    (out / "companies.js").write_text(cjs, encoding="utf-8")
    print(f"  company directory -> {len(companies['rows']):,} companies "
          f"({(out / 'companies.js').stat().st_size / 1e6:.1f} MB)")

    for name in APP_FILES:
        shutil.copyfile(APP_SRC / name, out / name)
    return out / "index.html"


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #


def main() -> int:
    print("Building the study pack")
    print(f"  output -> {config.OUT}")

    print("\n[1/6] Building the analysis context")
    ctx = ctxmod.build(verbose=True)

    print("\n[2/6] Running analysis modules")
    results, problems = run_modules(ctx)
    for p in problems:
        print(f"  !! {p}")

    print("\n[3/6] Writing tables and metrics")
    tables_written = write_tables(results)
    metrics_path = write_metrics_json(results)
    print(f"  {len(tables_written)} tables -> {config.OUT_DATA}")
    print(f"  metrics -> {metrics_path.name}")

    print("\n[4/6] Drawing charts")
    book = build_charts(ctx, results)
    print(f"  {len(book.records)} charts -> {config.OUT_CHARTS}")
    for f in book.failures:
        print(f"  !! {f['chart']}: {f['error']}")

    print("\n[5/6] Assembling the study pack")
    d, _ = build_study_pack(ctx, results, book, tables_written)
    write_outputs(d, book, tables_written, problems)
    print(f"  {config.OUT / 'STUDY_PACK.md'}")
    print(f"  {config.OUT / 'study_pack.html'}")
    print(f"  {config.OUT / 'README.md'}")

    print("\n[6/6] Building the browsable web app")
    app_path = write_web_app(ctx, results, book, tables_written)
    print(f"  {app_path}")

    if problems or book.failures:
        print("\nDONE with warnings "
              f"({len(problems)} module problems, "
              f"{len(book.failures)} chart failures)")
        return 1
    print("\nDONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
