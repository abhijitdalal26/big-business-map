"""Scrape Wikipedia's "List of largest <country> companies" pages.

Why this exists
---------------
The Forbes Global 2000 is an American list. It contains 612 US firms and
exactly zero Russian ones, and it misses the state-owned giants that dominate
revenue in much of the world. Wikipedia maintains a per-country list of the
largest firms, sourced from Forbes and Fortune, with revenue, profit, assets,
market value, employees and (for several countries) ownership.

Each page also carries a "Forbes 2000 rank" column, which lets us do two
things at once: measure how badly Forbes under-covers a country, and validate
the scraped numbers against the Forbes data we already hold.

Output: ``output/raw/wiki_country_companies.csv``
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import requests

from config import OUT_RAW

# --------------------------------------------------------------------------
# Pages to fetch: (wikipedia title, country, ISO3)
# --------------------------------------------------------------------------
PAGES: list[tuple[str, str, str]] = [
    ("List of largest German companies", "Germany", "DEU"),
    ("List of largest Chinese companies", "China", "CHN"),
    ("List of largest Japanese companies", "Japan", "JPN"),
    ("List of largest Indian companies", "India", "IND"),
    ("List of largest French companies", "France", "FRA"),
    ("List of largest Italian companies", "Italy", "ITA"),
    ("List of largest Spanish companies", "Spain", "ESP"),
    ("List of largest Brazilian companies", "Brazil", "BRA"),
    ("List of largest Canadian companies", "Canada", "CAN"),
    ("List of largest Australian companies", "Australia", "AUS"),
    ("List of largest Mexican companies", "Mexico", "MEX"),
    ("List of largest Polish companies", "Poland", "POL"),
    ("List of largest Swedish companies", "Sweden", "SWE"),
    ("List of largest Danish companies", "Denmark", "DNK"),
    ("List of largest Dutch companies", "Netherlands", "NLD"),
    ("List of largest Austrian companies", "Austria", "AUT"),
    ("List of largest Lithuanian companies", "Lithuania", "LTU"),
    ("List of largest companies in Belgium", "Belgium", "BEL"),
    ("List of largest companies in Finland", "Finland", "FIN"),
    ("List of largest companies in Indonesia", "Indonesia", "IDN"),
    ("List of largest companies in Ireland", "Ireland", "IRL"),
    ("List of largest companies in Israel", "Israel", "ISR"),
    ("List of largest companies in Malaysia", "Malaysia", "MYS"),
    ("List of largest companies in Nigeria", "Nigeria", "NGA"),
    ("List of largest companies in Pakistan", "Pakistan", "PAK"),
    ("List of largest companies in Saudi Arabia", "Saudi Arabia", "SAU"),
    ("List of largest companies in Singapore", "Singapore", "SGP"),
    ("List of largest companies in South Africa", "South Africa", "ZAF"),
    ("List of largest companies in Sri Lanka", "Sri Lanka", "LKA"),
    ("List of largest companies in Taiwan", "Taiwan", "TWN"),
    ("List of largest companies in Thailand", "Thailand", "THA"),
    ("List of largest companies in Vietnam", "Vietnam", "VNM"),
    ("List of largest companies in the Philippines", "Philippines", "PHL"),
    ("List of largest companies in the United Arab Emirates",
     "United Arab Emirates", "ARE"),
    ("List of largest companies in the United Kingdom", "United Kingdom", "GBR"),
    ("List of largest companies of South Korea", "South Korea", "KOR"),
    ("List of largest Russian companies", "Russia", "RUS"),
    ("List of largest Turkish companies", "Turkey", "TUR"),
    ("List of largest Norwegian companies", "Norway", "NOR"),
    ("List of largest New Zealand companies", "New Zealand", "NZL"),
    ("List of largest Portuguese companies", "Portugal", "PRT"),
    ("List of largest Greek companies", "Greece", "GRC"),
    ("List of largest Czech companies", "Czech Republic", "CZE"),
    ("List of largest Hungarian companies", "Hungary", "HUN"),
    ("List of largest Romanian companies", "Romania", "ROU"),
    ("List of largest Ukrainian companies", "Ukraine", "UKR"),
    ("List of largest Chilean companies", "Chile", "CHL"),
    ("List of largest Colombian companies", "Colombia", "COL"),
    ("List of largest Argentine companies", "Argentina", "ARG"),
    ("List of largest Peruvian companies", "Peru", "PER"),
    ("List of largest Egyptian companies", "Egypt", "EGY"),
    ("List of largest Moroccan companies", "Morocco", "MAR"),
    ("List of largest Kazakh companies", "Kazakhstan", "KAZ"),
    ("List of largest Luxembourgish companies", "Luxembourg", "LUX"),
    ("List of largest Irish companies", "Ireland", "IRL"),
    ("List of largest companies in Europe by revenue", "Europe", None),
    ("List of largest companies in Africa by revenue", "Africa", None),
    ("List of largest companies in Asia", "Asia", None),
    ("List of largest companies in Southeast Asia by revenue", "Southeast Asia", None),
    ("List of largest companies by revenue", "World", None),
    ("List of largest private companies by revenue", "World (private)", None),
    ("List of largest companies by number of employees", "World (employees)", None),
]

API = "https://en.wikipedia.org/api/rest_v1/page/html/"
HEADERS = {
    "User-Agent": (
        "company-data-analysis/1.0 (data journalism research script; "
        "single-run, low volume)"
    )
}

# Currency -> USD, static reference rates. Rows converted this way are
# flagged so the analysis can exclude or caveat them.
FX_TO_USD = {
    "USD": 1.0, "$": 1.0, "US$": 1.0,
    "EUR": 1.08, "€": 1.08,
    "GBP": 1.27, "£": 1.27,
    "JPY": 0.0067, "CNY": 0.138, "RMB": 0.138, "¥": 0.0067,
    "INR": 0.012, "₹": 0.012,
    "CAD": 0.73, "AUD": 0.66, "CHF": 1.13, "RUB": 0.011,
    "BRL": 0.18, "MXN": 0.055, "KRW": 0.00073, "TWD": 0.031,
    "SGD": 0.74, "HKD": 0.128, "ZAR": 0.055, "SEK": 0.095,
    "NOK": 0.093, "DKK": 0.145, "PLN": 0.25, "TRY": 0.029,
    "IDR": 0.000062, "THB": 0.027, "VND": 0.000039, "MYR": 0.21,
    "PHP": 0.017, "AED": 0.272, "SAR": 0.267, "ILS": 0.27,
    "NGN": 0.00062, "PKR": 0.0036, "EGP": 0.020, "CLP": 0.001,
    "COP": 0.00024, "ARS": 0.00098, "PEN": 0.26, "UAH": 0.024,
    "KZT": 0.002, "NZD": 0.60, "ILS ": 0.27,
}

NAME_PAT = re.compile(r"^(name|company|employer|conglomerate|firm)$", re.I)
REV_PAT = re.compile(r"(revenue|sales|turnover)", re.I)
PROFIT_PAT = re.compile(r"(profit|net income|earnings|net result)", re.I)
ASSET_PAT = re.compile(r"asset", re.I)
MCAP_PAT = re.compile(r"(market value|market cap|equity value|value)", re.I)
EMP_PAT = re.compile(r"(employee|workforce|staff)", re.I)
IND_PAT = re.compile(r"(industry|sector|field)", re.I)
HQ_PAT = re.compile(r"(headquarter|head office|city|location|domicile)", re.I)
OWN_PAT = re.compile(r"(ownership|owner|company type|type of ownership|status)", re.I)
RANK_PAT = re.compile(r"^(rank|no\.?|#|position|order)$", re.I)
FORBES_PAT = re.compile(r"forbes", re.I)
FORTUNE_PAT = re.compile(r"fortune", re.I)
YEAR_PAT = re.compile(r"(19|20)\d{2}", re.I)


def clean_text(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    s = str(v).replace("\xa0", " ")
    s = re.sub(r"\[\d+\]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return "" if s.lower() in {"nan", "none", "n/a", "-"} else s


def detect_scale(header: str) -> tuple[float, str]:
    """Return (multiplier, currency) implied by a column header."""
    h = clean_text(header)
    low = h.lower()
    currency = "USD"
    if "€" in h or "eur" in low:
        currency = "EUR"
    elif "£" in h or "gbp" in low:
        currency = "GBP"
    elif "¥" in h or "jpy" in low or "rmb" in low or "cny" in low:
        currency = "CNY" if ("rmb" in low or "cny" in low) else "JPY"
    elif "₹" in h or "inr" in low:
        currency = "INR"
    elif "r$" in low or "real" in low:
        currency = "BRL"

    if "trillion" in low:
        mult = 1e12
    elif "billion" in low or "bn" in low:
        mult = 1e9
    elif "million" in low or "mn" in low:
        mult = 1e6
    elif "thousand" in low or "k " in low:
        mult = 1e3
    else:
        mult = 1.0
    return mult, currency


def to_number(v) -> float | None:
    s = clean_text(v)
    if not s:
        return None
    s = s.replace("\u2212", "-").replace(",", "").replace("$", "")
    s = s.replace("€", "").replace("£", "").replace("%", "")
    s = s.replace(" ", "")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def classify_columns(cols: list[str]) -> dict[str, str]:
    """Map canonical field -> source column name."""
    out: dict[str, str] = {}
    for c in cols:
        c = str(c)
        if "forbes" in c.lower() and "forbes_rank" not in out:
            out["forbes_rank"] = c
        elif "fortune" in c.lower() and "fortune_rank" not in out:
            out["fortune_rank"] = c
        elif NAME_PAT.match(c.strip()) and "name" not in out:
            out["name"] = c
        elif RANK_PAT.match(c.strip()) and "rank" not in out:
            out["rank"] = c
        elif EMP_PAT.search(c) and "employees" not in out:
            out["employees"] = c
        elif IND_PAT.search(c) and "industry" not in out:
            out["industry"] = c
        elif HQ_PAT.search(c) and "headquarters" not in out:
            out["headquarters"] = c
        elif OWN_PAT.search(c) and "ownership" not in out:
            out["ownership"] = c
        elif REV_PAT.search(c) and "revenue" not in out:
            out["revenue"] = c
        elif PROFIT_PAT.search(c) and "profit" not in out:
            out["profit"] = c
        elif ASSET_PAT.search(c) and "assets" not in out:
            out["assets"] = c
        elif MCAP_PAT.search(c) and "market_cap" not in out:
            out["market_cap"] = c
    return out


def pick_table(tables: list[pd.DataFrame]) -> tuple[pd.DataFrame, dict] | None:
    """Choose the table that looks most like a company ranking."""
    best = None
    for t in tables:
        if t.shape[0] < 8 or t.shape[1] < 3:
            continue
        mapping = classify_columns([str(c) for c in t.columns])
        if "name" not in mapping:
            continue
        score = 0
        score += 3 if "revenue" in mapping else 0
        score += 2 if "profit" in mapping else 0
        score += 1 if "employees" in mapping else 0
        score += 1 if "forbes_rank" in mapping else 0
        score += 1 if "industry" in mapping else 0
        score += min(t.shape[0] / 50, 2)
        if best is None or score > best[0]:
            best = (score, t, mapping)
    if best is None or best[0] < 2:
        return None
    return best[1], best[2]


def extract_rows(t: pd.DataFrame, mapping: dict, page: str, country: str,
                 iso3: str | None) -> list[dict]:
    rows: list[dict] = []
    for _, r in t.iterrows():
        name = clean_text(r.get(mapping["name"], ""))
        if not name or len(name) < 2:
            continue
        rec: dict = {
            "company": name,
            "country": country,
            "country_iso3": iso3,
            "list_page": page,
            "rank_in_page": to_number(r.get(mapping["rank"])) if "rank" in mapping else None,
            "forbes2000_rank": to_number(r.get(mapping["forbes_rank"])) if "forbes_rank" in mapping else None,
            "fortune500_rank": to_number(r.get(mapping["fortune_rank"])) if "fortune_rank" in mapping else None,
            "industry": clean_text(r.get(mapping["industry"], "")) if "industry" in mapping else "",
            "headquarters": clean_text(r.get(mapping["headquarters"], "")) if "headquarters" in mapping else "",
            "ownership": clean_text(r.get(mapping["ownership"], "")) if "ownership" in mapping else "",
            "employees": to_number(r.get(mapping["employees"])) if "employees" in mapping else None,
            "source_table": "wiki",
        }
        for field in ("revenue", "profit", "assets", "market_cap"):
            if field not in mapping:
                rec[f"{field}_usd"] = None
                rec[f"{field}_fx"] = None
                continue
            raw = r.get(mapping[field])
            mult, cur = detect_scale(mapping[field])
            val = to_number(raw)
            if val is None:
                rec[f"{field}_usd"] = None
                rec[f"{field}_fx"] = None
                continue
            rate = FX_TO_USD.get(cur, 1.0)
            rec[f"{field}_usd"] = val * mult * rate
            rec[f"{field}_fx"] = cur if rate != 1.0 else None
        # A year mentioned in any column header is a useful vintage marker.
        rec["data_year"] = None
        for c in t.columns:
            m = YEAR_PAT.search(str(c))
            if m:
                rec["data_year"] = int(m.group(0))
                break
        rec["forbes2000_rank_note"] = (
            f"wiki page reports Forbes 2000 rank {int(rec['forbes2000_rank'])}"
            if rec.get("forbes2000_rank") else "")
        rows.append(rec)
    return rows


def fetch_html(title: str, session: requests.Session,
               tries: int = 5) -> str | None:
    """Fetch rendered HTML for a Wikipedia page.

    404 means the page does not exist -> give up.  403/429 mean the API is
    throttling us -> back off hard and retry, because those pages usually do
    exist and the next one in the list depends on them.
    """
    url = API + requests.utils.quote(title.replace(" ", "_"), safe="")
    for i in range(tries):
        try:
            r = session.get(url, timeout=45)
        except Exception:
            time.sleep(5 * (i + 1))
            continue
        if r.status_code == 200:
            return r.text
        if r.status_code == 404:
            return None
        wait = 6 * (i + 1)
        print(f"        HTTP {r.status_code} on {title}; waiting {wait}s")
        time.sleep(wait)
    return None


def parse_page(html: str) -> tuple[list[dict], str]:
    try:
        tables = pd.read_html(io.StringIO(html))
    except Exception:
        return [], ""
    chosen = pick_table(tables)
    if chosen is None:
        return [], ""
    t, mapping = chosen
    return t, " | ".join(f"{k}={v}" for k, v in mapping.items())


def main(limit: int | None = None, delay: float = 1.4,
         resume: bool = True) -> pd.DataFrame:
    session = requests.Session()
    session.headers.update(HEADERS)

    pages = PAGES[:limit] if limit else PAGES
    all_rows: list[dict] = []
    report: list[dict] = []
    missed: list[tuple[str, str, str | None]] = []

    out_dir = OUT_RAW
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "wiki_country_companies.csv"
    report_path = out_dir / "wiki_country_companies_report.csv"

    # Resume: keep whatever a previous (possibly interrupted) run collected.
    done_pages: set[str] = set()
    if resume and csv_path.exists():
        try:
            prev = pd.read_csv(csv_path)
            if len(prev):
                all_rows = prev.to_dict("records")
                done_pages = set(prev["list_page"].dropna())
                print(f"resuming: {len(all_rows):,} rows from {len(done_pages)} pages")
        except Exception:
            all_rows = []

    for n, (title, country, iso3) in enumerate(pages, 1):
        if title in done_pages:
            print(f"[{n:>2}/{len(pages)}] SKIP  {title} (already collected)")
            continue
        html = fetch_html(title, session)
        if html is None:
            report.append({"page": title, "country": country, "rows": 0,
                           "status": "missing"})
            missed.append((title, country, iso3))
            print(f"[{n:>2}/{len(pages)}] MISS  {title}")
            continue
        try:
            tables = pd.read_html(io.StringIO(html))
        except Exception as exc:
            report.append({"page": title, "country": country, "rows": 0,
                           "status": f"parse error: {exc}"})
            print(f"[{n:>2}/{len(pages)}] ERR   {title}: {exc}")
            continue

        chosen = pick_table(tables)
        if chosen is None:
            report.append({"page": title, "country": country, "rows": 0,
                           "status": "no usable table"})
            print(f"[{n:>2}/{len(pages)}]  --   {title}: no usable table")
            continue
        t, mapping = chosen
        rows = extract_rows(t, mapping, title, country, iso3)
        all_rows.extend(rows)
        report.append({"page": title, "country": country, "rows": len(rows),
                       "status": "ok",
                       "columns": ", ".join(mapping.keys())})
        print(f"[{n:>2}/{len(pages)}] OK    {title}  ({len(rows)} rows)")
        # Checkpoint after every page so an interrupted run is never lost.
        pd.DataFrame(all_rows).to_csv(csv_path, index=False, encoding="utf-8")
        time.sleep(delay)

    # Second pass: pages that were throttled on the first attempt.
    if missed:
        print(f"\nretry pass for {len(missed)} missed page(s)...")
        still_missed = []
        for title, country, iso3 in missed:
            time.sleep(3)
            html = fetch_html(title, session)
            if html is None:
                still_missed.append((title, country, iso3))
                continue
            try:
                tables = pd.read_html(io.StringIO(html))
            except Exception:
                still_missed.append((title, country, iso3))
                continue
            chosen = pick_table(tables)
            if chosen is None:
                still_missed.append((title, country, iso3))
                continue
            t, mapping = chosen
            rows = extract_rows(t, mapping, title, country, iso3)
            all_rows.extend(rows)
            for r in report:
                if r["page"] == title:
                    r.update({"rows": len(rows), "status": "ok (retry)",
                              "columns": ", ".join(mapping.keys())})
            print(f"  RETRY OK  {title}  ({len(rows)} rows)")
        for title, country, iso3 in still_missed:
            for r in report:
                if r["page"] == title:
                    r["status"] = "missing (after retry)"

    df = pd.DataFrame(all_rows)
    if len(df):
        df = df.drop_duplicates(subset=["company", "list_page"])
        df = df.sort_values(["country", "revenue_usd"], ascending=[True, False])

    OUT_RAW.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False, encoding="utf-8")
    pd.DataFrame(report).to_csv(report_path, index=False, encoding="utf-8")
    print(f"\nrows: {len(df):,}  countries: {df['country'].nunique() if len(df) else 0}")
    print(f"written -> {csv_path}")
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--delay", type=float, default=1.4)
    ap.add_argument("--no-resume", action="store_true")
    args = ap.parse_args()
    main(limit=args.limit, delay=args.delay, resume=not args.no_resume)
