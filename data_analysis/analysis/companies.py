"""Company directory -- one row per company in the reconciled universe.

Every other module answers a question about *groups* of firms. This one
answers the question a reader actually asks: "tell me about this company".
It joins the reconciled universe to whatever descriptive fields the source
files happen to carry -- official website, Wikipedia page, Forbes profile,
CEO, city, founding year and a one-line description -- so the study pack
can hand over a browsable directory instead of a pile of aggregates.

Nothing here is inferred. A blank cell means no source in this project
knows the value, and the coverage counts in the metrics say how many
companies that applies to.
"""

from __future__ import annotations

import pandas as pd

import clean

KEY = "companies"

#: Fields the directory keeps, in display order.
DIRECTORY_COLUMNS = [
    "company",
    "country",
    "country_iso3",
    "region",
    "sector",
    "industry_canon",
    "ownership",
    "source",
    "list_name",
    "n_sources",
    "confidence",
    "rank_in_source",
    "revenue_usd",
    "profit_usd",
    "assets_usd",
    "market_cap_usd",
    "valuation_usd",
    "employees",
    "revenue_year",
    "revenue_basis",
    "ticker",
    "website",
    "wikipedia",
    "forbes_page",
    "ceo",
    "city",
    "state",
    "year_founded",
    "description",
]

#: Which tagged detail column feeds which directory column, in priority
#: order.  Forbes wins over Fortune for a website because it is the wider
#: and more current file; Fortune fills the gaps.
_DETAIL_PRIORITY = {
    "website": ("website__fb", "website__ft"),
    "description": ("description__fb", "description__ls"),
    "wikipedia": ("wikipedia__ls",),
    "forbes_page": ("forbes_page__fb",),
    "ceo": ("ceo__fb",),
    "city": ("city__fb", "city"),
    "state": ("state__fb", "state"),
    "year_founded": ("year_founded__fb",),
    "ticker": ("ticker__ls",),
}


def _norm_url(value: object) -> str:
    """Return a clean http(s) URL, or "" when nothing usable is there."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "-", "n/a"}:
        return ""
    if not text.lower().startswith(("http://", "https://")):
        text = "https://" + text
    return text


def _wiki_url(title: object) -> str:
    """Wikipedia article URL for a page title, or ""."""
    text = str(title or "").strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return ""
    return "https://en.wikipedia.org/wiki/" + text.replace(" ", "_")


def _text(value: object) -> str:
    """Trimmed string for any scalar, with NaN turned into ""."""
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def _forbes_detail(bundle) -> pd.DataFrame:
    """Descriptive fields from the raw Forbes Global 2000 file."""
    raw = bundle.get("forbes2000")
    cols = ["company_key", "website__fb", "forbes_page__fb", "description__fb",
            "ceo__fb", "city__fb", "state__fb", "year_founded__fb"]
    if raw is None or not len(raw):
        return pd.DataFrame(columns=cols)
    fr = raw.copy()
    fr["company_key"] = fr["company"].map(clean.company_key)
    fr = fr.drop_duplicates(subset=["company_key"])
    out = pd.DataFrame({"company_key": fr["company_key"]})
    out["website__fb"] = fr["website"].map(_norm_url) if "website" in fr else ""
    if "uri" in fr:
        uri = fr["uri"].map(_text)
        out["forbes_page__fb"] = [
            f"https://www.forbes.com/companies/{u}/" if u else "" for u in uri]
    else:
        out["forbes_page__fb"] = ""
    out["description__fb"] = fr["description"].map(_text) if "description" in fr else ""
    out["ceo__fb"] = fr["ceo"].map(_text) if "ceo" in fr else ""
    out["city__fb"] = fr["city"].map(_text) if "city" in fr else ""
    out["state__fb"] = fr["state"].map(_text) if "state" in fr else ""
    out["year_founded__fb"] = (fr["year_founded"].map(_text)
                               if "year_founded" in fr else "")
    return out


def _fortune_detail(bundle) -> pd.DataFrame:
    """Websites for the Fortune Global 500."""
    profiles = bundle.get("fortune_profiles")
    if profiles is None or not len(profiles):
        return pd.DataFrame(columns=["company_key", "website__ft"])
    fp = profiles.copy()
    ranking = bundle.get("fortune500")
    if ranking is not None and len(ranking) and "slug" in ranking \
            and "company" in ranking:
        fp = fp.merge(ranking[["slug", "company"]], on="slug", how="left")
    elif "company" not in fp:
        return pd.DataFrame(columns=["company_key", "website__ft"])
    fp["company_key"] = fp["company"].map(clean.company_key)
    fp = fp.drop_duplicates(subset=["company_key"])
    out = pd.DataFrame({"company_key": fp["company_key"]})
    out["website__ft"] = fp["website"].map(_norm_url) if "website" in fp else ""
    return out


def _listed_detail(bundle) -> pd.DataFrame:
    """Wikipedia links, tickers and descriptions for listed companies."""
    profiles = bundle.get("profiles")
    cols = ["company_key", "wikipedia__ls", "ticker__ls", "description__ls"]
    if profiles is None or not len(profiles):
        return pd.DataFrame(columns=cols)
    pr = profiles.copy()
    pr["company_key"] = pr["company"].map(clean.company_key)
    pr = pr.drop_duplicates(subset=["company_key"])
    out = pd.DataFrame({"company_key": pr["company_key"]})
    out["wikipedia__ls"] = pr["wiki_title"].map(_wiki_url) if "wiki_title" in pr else ""
    if "ticker_or_slug" in pr:
        tick = pr["ticker_or_slug"].map(_text)
        # Only real tickers are short and upper-case; anything else is a
        # data-provider slug, which a reader cannot trade with.
        out["ticker__ls"] = [
            t if (t and len(t) <= 6 and t.isupper()) else "" for t in tick]
    else:
        out["ticker__ls"] = ""
    out["description__ls"] = (pr["description"].map(_text)
                              if "description" in pr else "")
    return out


def _first_present(frame: pd.DataFrame, columns: tuple[str, ...]) -> pd.Series:
    """First non-empty value across the given columns, as a Series."""
    result = pd.Series("", index=frame.index, dtype="object")
    for col in columns:
        if col not in frame.columns:
            continue
        values = frame[col].map(lambda v: v if isinstance(v, str) else _text(v))
        result = result.where(result != "", values)
    return result


def run(ctx) -> dict:
    rec = ctx.reconciled.copy()
    rec["company_key"] = rec["company_key"].astype(str)

    parts = []
    for detail in (_forbes_detail(ctx.bundle),
                   _fortune_detail(ctx.bundle),
                   _listed_detail(ctx.bundle)):
        if len(detail):
            # Index by company key so the three sources line up by company,
            # not by row position.
            parts.append(detail.drop_duplicates(subset=["company_key"], keep="first")
                         .set_index("company_key"))
    if parts:
        detail = pd.concat(parts, axis=1)
        detail = detail.loc[:, ~detail.columns.duplicated()]
        rec = rec.merge(detail.reset_index(), on="company_key", how="left")

    for field, columns in _DETAIL_PRIORITY.items():
        rec[field] = _first_present(rec, columns)
    rec["website"] = rec["website"].map(_norm_url)
    rec["forbes_page"] = rec["forbes_page"].map(_norm_url)
    # The Wikipedia column already holds a full article URL -- the detail
    # builder built it that way -- so it is only tidied, never rebuilt.
    rec["wikipedia"] = rec["wikipedia"].map(
        lambda v: v if isinstance(v, str) else _text(v))

    # -- sector, from the project taxonomy ------------------------------
    # The taxonomy maps a canonical industry onto a sector.  Where a company
    # has a canonical industry but no sector, the sector is a lookup rather
    # than a judgement, so we take it.
    if "sector" not in rec.columns:
        rec["sector"] = ""
    if "industry_canon" not in rec.columns:
        rec["industry_canon"] = ""
    taxonomy = ctx.bundle.get("industry_taxonomy")
    if taxonomy is not None and len(taxonomy) \
            and "industry_canon" in taxonomy.columns \
            and "sector" in taxonomy.columns:
        sector_by_industry = {
            _text(k): _text(v)
            for k, v in zip(taxonomy["industry_canon"], taxonomy["sector"])
            if _text(k) and _text(v)}
        blank_sector = (rec["sector"].isna()
                        | (rec["sector"].astype(str).str.strip() == "")
                        | (rec["sector"].astype(str).str.strip().str.lower()
                           == "unclassified"))
        filled = rec["industry_canon"].map(sector_by_industry)
        use = blank_sector & (filled != "")
        rec.loc[use, "sector"] = filled[use]

    # -- region, from the country index ---------------------------------
    # ``forbes_region`` is the vocabulary the rest of the pack uses; the
    # plain ``region`` column is the World Bank's, so it is only a fallback.
    if "region" not in rec.columns:
        rec["region"] = ""
    idx = ctx.idx
    if idx is not None and len(idx) and "iso3" in idx.columns:
        source_col = ("forbes_region" if "forbes_region" in idx.columns
                      else ("region" if "region" in idx.columns else None))
        if source_col:
            region_by_iso = {str(i): _text(r)
                             for i, r in zip(idx["iso3"], idx[source_col])}
            unknown = (rec["region"].isna()
                       | (rec["region"].astype(str).str.strip() == "")
                       | (rec["region"].astype(str).str.strip().str.lower()
                          == "unknown"))
            filled = rec["country_iso3"].map(
                lambda iso: region_by_iso.get(str(iso), ""))
            use = unknown & (filled != "")
            rec.loc[use, "region"] = filled[use]

    directory = rec.reindex(columns=[c for c in DIRECTORY_COLUMNS if c in rec.columns])
    directory = directory.sort_values(
        ["revenue_usd", "market_cap_usd"], ascending=False, na_position="last")
    directory = directory.reset_index(drop=True)

    # -- presence table: one row per company, sized for a dot plot ------
    presence = rec[["company", "country_iso3", "sector", "ownership", "source",
                    "revenue_usd", "market_cap_usd", "employees"]].copy()
    presence = presence.sort_values("revenue_usd", ascending=False, na_position="last")
    presence["rank_by_revenue"] = range(1, len(presence) + 1)
    presence = presence.reset_index(drop=True)

    def _count(col: str) -> int:
        if col not in directory.columns:
            return 0
        series = directory[col]
        return int(((series.notna()) & (series.astype(str).str.strip() != "")).sum())

    def _top(by: str, value: str, n: int = 12) -> list[dict]:
        if by not in directory.columns or value not in directory.columns:
            return []
        grouped = (directory.groupby(by, dropna=True)[value]
                   .agg(["sum", "count"]).reset_index()
                   .sort_values("sum", ascending=False))
        return [{"name": _text(r[by]), "value": float(r["sum"]),
                 "firms": int(r["count"])}
                for _, r in grouped.head(n).iterrows()]

    metrics = {
        "companies": int(len(directory)),
        "with_website": _count("website"),
        "with_wikipedia": _count("wikipedia"),
        "with_forbes_page": _count("forbes_page"),
        "with_description": _count("description"),
        "with_ceo": _count("ceo"),
        "with_revenue": int(directory["revenue_usd"].notna().sum())
        if "revenue_usd" in directory else 0,
        "with_market_cap": int(directory["market_cap_usd"].notna().sum())
        if "market_cap_usd" in directory else 0,
        "with_profit": int(directory["profit_usd"].notna().sum())
        if "profit_usd" in directory else 0,
        "with_employees": int(directory["employees"].notna().sum())
        if "employees" in directory else 0,
        "with_country": _count("country"),
        "by_source": {str(k): int(v) for k, v in
                      rec["source"].value_counts().items()} if "source" in rec else {},
        "by_ownership": {str(k): int(v) for k, v in
                         rec["ownership"].value_counts().items()}
        if "ownership" in rec else {},
        "by_sector": _top("sector", "revenue_usd", 14),
        "by_country": _top("country", "revenue_usd", 16),
        "coverage_rule": (
            "A blank cell means no source in this project carries the value. "
            "Websites come from the Forbes Global 2000 and Fortune Global 500 "
            "files; Wikipedia links from the listed-universe company profiles."),
    }
    if "revenue_usd" in directory and directory["revenue_usd"].notna().any():
        metrics["revenue_total_usd"] = float(directory["revenue_usd"].sum())
    if "market_cap_usd" in directory and directory["market_cap_usd"].notna().any():
        metrics["market_cap_total_usd"] = float(directory["market_cap_usd"].sum())

    tables = {
        "company_directory": directory,
        "company_presence": presence,
    }
    return {"key": KEY, "metrics": metrics, "tables": tables}


def insights(m: dict) -> list[str]:
    total = int(m.get("companies", 0))
    website = int(m.get("with_website", 0))
    wiki = int(m.get("with_wikipedia", 0))
    desc = int(m.get("with_description", 0))
    rev = int(m.get("with_revenue", 0))
    cap = int(m.get("with_market_cap", 0))
    listed = int((m.get("by_source") or {}).get("listed", 0))
    out = [
        f"The directory holds **{total:,} companies** -- every firm the "
        f"reconciliation could name. **{rev:,}** carry a revenue figure, "
        f"**{cap:,}** a market value, and only **{listed:,}** of them have a "
        f"listed share.",
        f"Descriptive detail is patchy by design rather than by accident: "
        f"**{website:,}** companies have an official website, **{wiki:,}** a "
        f"Wikipedia article and **{desc:,}** a one-line description. The rest "
        f"are numbers without a face, and this pack does not invent one.",
    ]
    top_sector = (m.get("by_sector") or [None])[0]
    if top_sector:
        out.append(
            f"By measured revenue the largest sector is **{top_sector['name']}** "
            f"with {top_sector['firms']:,} firms and "
            f"${top_sector['value'] / 1e9:,.0f}B of revenue.")
    return out
