"""Profitability and size data for the listed universe.

Stages (each cached under listed_universe/data/raw_fin/, so every stage resumes):

  sec       SEC XBRL frames (authoritative, US filers)
              duration: NetIncomeLoss (fallback ProfitLoss), OperatingIncomeLoss
                        CY2025, fallback CY2024
              instant : Assets, StockholdersEquity (fallback incl. NCI)
                        CY2025Q4I, fallback CY2024Q4I
              dei     : EntityNumberOfEmployees (instant frames; very sparse)
  cmc       companiesmarketcap.com per-company pages (estimate-grade)
              /<slug>/earnings/  -> pre-tax income, TTM
              /<slug>/pe-ratio/  -> P/E (TTM)
            CMC's /<slug>/employees/ page exists but carries no data
            ("Unfortunately we have no employee count data") even for Apple or
            Walmart, so employees come from Wikidata instead.
  wikidata  employees (P1128) for companies with a confirmed Wikipedia title in
            company_profiles.csv (estimate-grade, latest point-in-time value)
  build     merge -> data/universe_financials.csv, rejections -> data/raw_fin/rejected.csv

Usage:
  python fetch_financials.py sec
  python fetch_financials.py cmc [--limit N] [--pages earnings,pe]
  python fetch_financials.py wikidata
  python fetch_financials.py build
  python fetch_financials.py all
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

DATA = Path(__file__).resolve().parents[1] / "data"
RAW = DATA / "raw_fin"
SEC_UA = {"User-Agent": "EarthBusinessAtlas research abhijitdalal2609@gmail.com"}
CMC_UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
}
CMC = "https://companiesmarketcap.com"

# ----------------------------------------------------------------------------- SEC

DURATION = {  # field -> tags in preference order
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "operating_income": ["OperatingIncomeLoss"],
}
INSTANT = {
    "assets": ["Assets"],
    "equity": ["StockholdersEquity",
               "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
}
DUR_PERIODS = ["CY2025", "CY2024"]
INST_PERIODS = ["CY2025Q4I", "CY2024Q4I"]
EMP_PERIODS = ["CY2025Q4I", "CY2025Q3I", "CY2025Q2I", "CY2025Q1I",
               "CY2024Q4I", "CY2024Q3I", "CY2024Q2I", "CY2024Q1I"]


def sec_frame(taxonomy: str, tag: str, unit: str, period: str) -> list[dict]:
    cache = RAW / "sec" / f"{taxonomy}_{tag}_{unit}_{period}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8")).get("data", [])
    url = f"https://data.sec.gov/api/xbrl/frames/{taxonomy}/{tag}/{unit}/{period}.json"
    for attempt in range(4):
        try:
            r = requests.get(url, headers=SEC_UA, timeout=90)
            if r.status_code == 404:
                cache.write_text('{"data": []}', encoding="utf-8")
                return []
            r.raise_for_status()
            cache.write_bytes(r.content)
            time.sleep(0.2)                        # SEC asks for <=10 req/s
            return r.json().get("data", [])
        except Exception as exc:  # noqa: BLE001
            print(f"    retry {tag}/{period}: {exc}")
            time.sleep(2 * (attempt + 1))
    return []


def stage_sec() -> None:
    (RAW / "sec").mkdir(parents=True, exist_ok=True)
    out: dict[int, dict] = {}

    def take(field, taxonomy, tags, unit, periods):
        # period first, then tag: a CY2025 ProfitLoss beats a CY2024 NetIncomeLoss
        for period in periods:
            for tag in tags:
                n = 0
                for rec in sec_frame(taxonomy, tag, unit, period):
                    cik, val = rec.get("cik"), rec.get("val")
                    if cik is None or val is None:
                        continue
                    row = out.setdefault(cik, {"cik": cik, "entity_name": rec.get("entityName")})
                    if f"{field}_usd" in row:
                        continue
                    row[f"{field}_usd"] = float(val)
                    row[f"{field}_tag"] = tag
                    row[f"{field}_period"] = period
                    n += 1
                print(f"  {field:17s} {period:10s} {tag}: +{n}")

    for field, tags in DURATION.items():
        take(field, "us-gaap", tags, "USD", DUR_PERIODS)
    for field, tags in INSTANT.items():
        take(field, "us-gaap", tags, "USD", INST_PERIODS)
    take("employees", "dei", ["EntityNumberOfEmployees"], "pure", EMP_PERIODS)

    df = pd.DataFrame(out.values())
    if "employees_usd" in df:
        df = df.rename(columns={"employees_usd": "employees"})
    df.to_csv(RAW / "sec_financials.csv", index=False, encoding="utf-8-sig")
    print(f"wrote {RAW / 'sec_financials.csv'} rows={len(df)}")


# ----------------------------------------------------------------------------- CMC

UNIT = {"Billion": 1e9, "Million": 1e6, "Trillion": 1e12, "Thousand": 1e3}
EARN_RE = re.compile(
    r"Earnings in (?P<year>\d{4})(?P<ttm> \(TTM\))?:\s*<span[^>]*>\s*(?P<neg>-)?\$(?P<val>[\d.,]+)"
    r"\s*(?P<unit>Trillion|Billion|Million|Thousand)?\s*USD"
)
PE_RE = re.compile(
    r"P/E ratio (?:as of|at the end of) (?P<asof>(?:[A-Za-z]+ )?\d{4})(?: \(TTM\))?:\s*<span[^>]*>"
    r"\s*(?P<val>-?[\d.,]+)"
)
PAGES = {"earnings": "earnings", "pe": "pe-ratio"}


class RateLimiter:
    def __init__(self, per_sec: float):
        self.gap = 1.0 / per_sec
        self.lock = threading.Lock()
        self.next = 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            t = max(now, self.next)
            self.next = t + self.gap
        time.sleep(max(0.0, t - time.monotonic()))


_local = threading.local()


def session() -> requests.Session:
    if not hasattr(_local, "s"):
        _local.s = requests.Session()
        _local.s.headers.update(CMC_UA)
    return _local.s


def cmc_get(url: str, limiter: RateLimiter, tries: int = 4):
    """Return (status, text). status: 'ok', '404', 'fail'."""
    for i in range(tries):
        limiter.wait()
        try:
            r = session().get(url, timeout=30, allow_redirects=False)
            if r.status_code == 200:
                return "ok", r.content.decode("utf-8", errors="replace")
            if r.status_code in (301, 302) and "404" in r.headers.get("Location", ""):
                return "404", None
            if r.status_code == 404:
                return "404", None
            if r.status_code == 429:
                time.sleep(20 * (i + 1))
        except Exception as exc:  # noqa: BLE001
            print(f"    retry {url}: {exc}", flush=True)
        time.sleep(1.5 * (i + 1))
    return "fail", None


def parse(kind: str, html: str) -> dict:
    if kind == "earnings":
        m = EARN_RE.search(html)
        if not m:
            return {"value": None}
        v = float(m.group("val").replace(",", "")) * UNIT.get(m.group("unit") or "", 1.0)
        return {"value": -v if m.group("neg") else v,
                "period": m.group("year") + (" TTM" if m.group("ttm") else "")}
    m = PE_RE.search(html)
    if not m:
        return {"value": None}
    return {"value": float(m.group("val").replace(",", "")), "period": m.group("asof")}


def stage_cmc(limit: int, kinds: list[str], rate: float) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    lst = pd.read_csv(DATA / "cmc_list.csv", encoding="utf-8-sig")
    uni = pd.read_csv(DATA / "listed_universe.csv", encoding="utf-8-sig")
    lst = lst[lst.slug.isin(set(uni.ticker_or_slug.dropna()))]
    slugs = (lst.sort_values("market_cap_usd", ascending=False)
                .drop_duplicates("slug").slug.tolist())[:limit]
    limiter = RateLimiter(rate)

    for kind in kinds:                         # earnings first, then P/E
        path = RAW / f"cmc_{kind}.jsonl"
        done = set()
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec.get("status") != "fail":
                    done.add(rec["slug"])
        todo = [s for s in slugs if s not in done]
        print(f"cmc {kind}: {len(todo)} to fetch ({len(done)} cached)", flush=True)

        def one(slug: str) -> dict:
            status, html = cmc_get(f"{CMC}/{slug}/{PAGES[kind]}/", limiter)
            rec = {"slug": slug, "status": status, "value": None, "period": None}
            if html:
                rec.update(parse(kind, html))
                if rec["value"] is None:
                    rec["status"] = "nodata"
            return rec

        t0 = time.time()
        with path.open("a", encoding="utf-8") as fh, ThreadPoolExecutor(max_workers=4) as pool:
            futs = [pool.submit(one, s) for s in todo]
            for i, fut in enumerate(as_completed(futs), 1):
                fh.write(json.dumps(fut.result()) + "\n")
                fh.flush()
                if i % 250 == 0:
                    rate_now = i / (time.time() - t0)
                    print(f"  {kind} {i}/{len(todo)}  {rate_now:.1f}/s", flush=True)
        print(f"cmc {kind}: done", flush=True)


def load_jsonl(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["slug", "status", "value", "period"])
    recs = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r["slug"] not in recs or recs[r["slug"]]["status"] == "fail":
            recs[r["slug"]] = r
    return pd.DataFrame(recs.values())


# ----------------------------------------------------------------------------- Wikidata

def wd_get(url: str, params: dict, cache: Path):
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    for i in range(4):
        try:
            r = requests.get(url, params=params, headers=SEC_UA, timeout=60)
            if r.status_code == 200:
                cache.write_bytes(r.content)
                time.sleep(0.3)
                return r.json()
            if r.status_code == 429:
                time.sleep(30)
        except Exception as exc:  # noqa: BLE001
            print(f"    retry wikidata: {exc}")
        time.sleep(2 * (i + 1))
    return {}


def latest_quantity(claims: list[dict]):
    best, best_key = None, None
    for c in claims:
        if c.get("rank") == "deprecated":
            continue
        dv = c.get("mainsnak", {}).get("datavalue", {}).get("value")
        if not isinstance(dv, dict) or "amount" not in dv:
            continue
        pit = c.get("qualifiers", {}).get("P585", [{}])[0].get("datavalue", {}) \
               .get("value", {}).get("time", "") or ""
        key = (c.get("rank") == "preferred", pit)
        if best_key is None or key > best_key:
            best, best_key = (float(dv["amount"]), pit[1:5] if pit else None), key
    return best


def stage_wikidata() -> None:
    d = RAW / "wikidata"
    d.mkdir(parents=True, exist_ok=True)
    prof = pd.read_csv(DATA / "company_profiles.csv", encoding="utf-8-sig",
                       usecols=["ticker_or_slug", "company", "wiki_title"])
    titles = sorted(set(prof.wiki_title.dropna()))
    print(f"wikidata: {len(titles)} titles")

    # 1. title -> QID via Wikipedia pageprops (follows redirects)
    t2q: dict[str, str] = {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        js = wd_get("https://en.wikipedia.org/w/api.php",
                    {"action": "query", "prop": "pageprops", "ppprop": "wikibase_item",
                     "redirects": 1, "format": "json", "titles": "|".join(batch)},
                    d / f"titles_{i:05d}.json")
        q = js.get("query", {})
        alias = {}
        for n in q.get("normalized", []) + q.get("redirects", []):
            alias[n["to"]] = alias.get(n["from"], n["from"])
        for p in q.get("pages", {}).values():
            qid = p.get("pageprops", {}).get("wikibase_item")
            if qid:
                t = p["title"]
                t2q[t] = qid
                src = t
                while src in alias:           # map back to the original title
                    src = alias[src]
                    t2q[src] = qid
    print(f"  QIDs: {len(t2q)}")

    # 2. QID -> P1128 employees
    qids = sorted(set(t2q.values()))
    emp: dict[str, tuple] = {}
    for i in range(0, len(qids), 50):
        js = wd_get("https://www.wikidata.org/w/api.php",
                    {"action": "wbgetentities", "ids": "|".join(qids[i:i + 50]),
                     "props": "claims", "format": "json"},
                    d / f"entities_{i:05d}.json")
        for qid, ent in js.get("entities", {}).items():
            v = latest_quantity(ent.get("claims", {}).get("P1128", []))
            if v:
                emp[qid] = v
        if i % 1000 == 0:
            print(f"  entities {i}/{len(qids)}  employees so far {len(emp)}", flush=True)

    rows = []
    for _, r in prof.dropna(subset=["wiki_title"]).iterrows():
        qid = t2q.get(r.wiki_title)
        if qid and qid in emp:
            rows.append({"ticker_or_slug": r.ticker_or_slug, "company": r.company,
                         "wiki_title": r.wiki_title, "qid": qid,
                         "employees": emp[qid][0], "employees_year": emp[qid][1]})
    pd.DataFrame(rows).to_csv(RAW / "wikidata_employees.csv", index=False, encoding="utf-8-sig")
    print(f"wrote wikidata_employees.csv rows={len(rows)}")


# ----------------------------------------------------------------------------- build

def stage_build() -> None:
    uni = pd.read_csv(DATA / "listed_universe.csv", encoding="utf-8-sig")
    sec = pd.read_csv(RAW / "sec_financials.csv", encoding="utf-8-sig") \
        if (RAW / "sec_financials.csv").exists() else pd.DataFrame(columns=["cik"])
    sec = sec.set_index("cik")
    earn = load_jsonl(RAW / "cmc_earnings.jsonl").set_index("slug")
    pe = load_jsonl(RAW / "cmc_pe.jsonl").set_index("slug")
    wd_path = RAW / "wikidata_employees.csv"
    wd = pd.read_csv(wd_path, encoding="utf-8-sig") if wd_path.exists() else pd.DataFrame()
    # wikidata keyed by (company, slug) because SEC-only rows have no slug
    wd_key = {(r.company, r.ticker_or_slug if isinstance(r.ticker_or_slug, str) else ""):
              (r.employees, r.employees_year) for r in wd.itertuples()} if len(wd) else {}

    rejected = []
    out = []
    for r in uni.itertuples():
        slug = r.ticker_or_slug if isinstance(r.ticker_or_slug, str) else None
        cik = int(r.cik) if pd.notna(r.cik) else None
        rev = r.revenue_usd if pd.notna(r.revenue_usd) else None
        row = {"company": r.company, "ticker_or_slug": slug, "cik": cik,
               "net_income_usd": None, "net_income_source": None,
               "pretax_earnings_usd": None, "operating_income_usd": None,
               "assets_usd": None, "equity_usd": None,
               "employees": None, "employees_source": None, "pe_ratio": None,
               "period": None, "confidence": None}
        periods = []

        def check(field, val, source):
            if val is None or pd.isna(val):
                return None
            if rev and rev > 1e9 and abs(val) > 2 * rev:
                rejected.append({"company": r.company, "ticker_or_slug": slug, "cik": cik,
                                 "field": field, "value": val, "revenue_usd": rev,
                                 "source": source, "reason": "|value| > 2x revenue"})
                return None
            return float(val)

        if cik is not None and cik in sec.index:
            s = sec.loc[cik]
            v = check("net_income_usd", s.get("net_income_usd"), "SEC")
            if v is not None:
                row["net_income_usd"] = v
                row["net_income_source"] = f"SEC XBRL {s.net_income_tag}"
                periods.append(f"NI {s.net_income_period}")
            v = check("operating_income_usd", s.get("operating_income_usd"), "SEC")
            if v is not None:
                row["operating_income_usd"] = v
                periods.append(f"OI {s.operating_income_period}")
            if pd.notna(s.get("assets_usd")):
                row["assets_usd"] = float(s.assets_usd)
                periods.append(f"BS {s.assets_period}")
            if pd.notna(s.get("equity_usd")):
                row["equity_usd"] = float(s.equity_usd)
            e = s.get("employees")
            if pd.notna(e) and e > 0:
                if e > 3e6:
                    rejected.append({"company": r.company, "ticker_or_slug": slug, "cik": cik,
                                     "field": "employees", "value": e, "revenue_usd": rev,
                                     "source": "SEC dei", "reason": "> 3M employees"})
                else:
                    row["employees"], row["employees_source"] = int(e), \
                        f"SEC dei EntityNumberOfEmployees {s.employees_period}"

        if slug and slug in earn.index and earn.loc[slug, "status"] == "ok":
            v = check("pretax_earnings_usd", earn.loc[slug, "value"], "CMC")
            if v is not None:
                row["pretax_earnings_usd"] = v
                periods.append(f"PTI {earn.loc[slug, 'period']}")
        if slug and slug in pe.index and pe.loc[slug, "status"] == "ok":
            row["pe_ratio"] = float(pe.loc[slug, "value"])

        if row["employees"] is None:
            w = wd_key.get((r.company, slug or ""))
            if w:
                e, yr = w
                if e > 3e6:
                    rejected.append({"company": r.company, "ticker_or_slug": slug, "cik": cik,
                                     "field": "employees", "value": e, "revenue_usd": rev,
                                     "source": "Wikidata", "reason": "> 3M employees"})
                elif e > 0:
                    row["employees"] = int(e)
                    row["employees_source"] = "Wikidata P1128" + (f" {int(yr)}" if pd.notna(yr) and yr else "")

        row["period"] = "; ".join(periods) or None
        has_sec = row["net_income_source"] or row["assets_usd"] is not None
        row["confidence"] = "authoritative" if has_sec else (
            "estimate" if any(row[k] is not None for k in
                              ("pretax_earnings_usd", "pe_ratio", "employees")) else None)
        out.append(row)

    df = pd.DataFrame(out)
    for c in ("cik", "employees"):
        df[c] = df[c].astype("Int64")
    df.to_csv(DATA / "universe_financials.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(rejected).to_csv(RAW / "rejected.csv", index=False, encoding="utf-8-sig")
    print(f"wrote universe_financials.csv rows={len(df)}; rejected={len(rejected)}")
    report(df, uni)


def report(df: pd.DataFrame, uni: pd.DataFrame) -> None:
    mc = uni.market_cap_usd.fillna(0)
    tot = mc.sum()
    print(f"{'field':22s} {'rows':>7s} {'%rows':>6s} {'%mcap':>6s}")
    for c in ["net_income_usd", "pretax_earnings_usd", "operating_income_usd", "assets_usd",
              "equity_usd", "employees", "pe_ratio"]:
        m = df[c].notna()
        print(f"{c:22s} {m.sum():7d} {m.mean():6.1%} {mc[m].sum() / tot:6.1%}")
    m = df.net_income_usd.notna() | df.pretax_earnings_usd.notna()
    print(f"{'any earnings':22s} {m.sum():7d} {m.mean():6.1%} {mc[m].sum() / tot:6.1%}")
    print(df.employees_source.str.split().str[:2].str.join(" ").value_counts().to_string())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["sec", "cmc", "wikidata", "build", "all"])
    ap.add_argument("--limit", type=int, default=100000)
    ap.add_argument("--pages", default="earnings,pe")
    ap.add_argument("--rate", type=float, default=4.0, help="CMC requests per second")
    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    if a.stage in ("sec", "all"):
        stage_sec()
    if a.stage in ("cmc", "all"):
        stage_cmc(a.limit, a.pages.split(","), a.rate)
    if a.stage in ("wikidata", "all"):
        stage_wikidata()
    if a.stage in ("build", "all"):
        stage_build()


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    main()
