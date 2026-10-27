"""Assign the project's sector / industry_canon to every row of the listed universe.

Taxonomy = data/industry_taxonomy.csv (13 sectors, 30 industries), the same one the
Forbes Global 2000 analysis uses, so the two line up.

Sources, in priority order (each row records which one won):
  1. forbes    - Forbes Global 2000 match (CMC slug == Forbes uri, or exact normalised name)
  2. sec_sic   - SEC SIC code for US filers with a CIK (data.sec.gov submissions API)
  3. cmc       - CompaniesMarketCap category pages (slug -> categories)
  4. wikidata  - Wikidata "industry" (P452) via the enwiki sitelink of the Wikipedia title
  5. keyword   - regex rules on the description text (last resort)
  plus a small `manual` override table for spot-check corrections.

Stages (all cached in listed_universe/data/raw_sector/, resumable):
  python classify_sectors.py fetch-sec
  python classify_sectors.py fetch-cmc
  python classify_sectors.py fetch-wikidata
  python classify_sectors.py build          -> data/universe_sectors.csv
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve()
LU = HERE.parents[1]
ROOT = HERE.parents[2]
DATA = LU / "data"
RAW = DATA / "raw_sector"
RAW.mkdir(exist_ok=True)

BROWSER_UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
}
SEC_UA = {"User-Agent": "EarthBusinessAtlas research abhijitdalal2609@gmail.com",
          "Accept-Encoding": "gzip, deflate"}
WD_UA = {"User-Agent": "EarthBusinessAtlas research (abhijitdalal2609@gmail.com) python-requests"}
CMC = "https://companiesmarketcap.com"


def fetch(url, session, tries=4, params=None, pause=1.0):
    for i in range(tries):
        try:
            r = session.get(url, timeout=40, params=params)
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                return None
            if r.status_code in (429, 503):
                time.sleep(10 * (i + 1))
                continue
            print(f"    HTTP {r.status_code} {url}")
        except Exception as exc:  # noqa: BLE001
            print(f"    retry {url}: {exc}")
        time.sleep(pause * (i + 1))
    return None


def load_universe():
    import pandas as pd
    u = pd.read_csv(DATA / "listed_universe.csv")
    p = pd.read_csv(DATA / "company_profiles.csv")
    assert len(u) == len(p) and (u.company.values == p.company.values).all()
    u["description"] = p["description"].values
    u["wiki_title"] = p["wiki_title"].values
    u["cik"] = u["cik"].astype("Int64")
    return u


# ------------------------------------------------------------------ 1. SEC SIC
SEC_CACHE = RAW / "sec_sic.jsonl"


def fetch_sec():
    """SIC per CIK. ~1s latency per call, so 5 worker threads share one rate limiter
    that never starts more than 7 requests per second (SEC limit is 10)."""
    import threading
    from concurrent.futures import ThreadPoolExecutor

    u = load_universe()
    ciks = sorted({int(c) for c in u.cik.dropna()})
    done = set()
    if SEC_CACHE.exists():
        for line in SEC_CACHE.open(encoding="utf-8"):
            done.add(json.loads(line)["cik"])
    todo = [c for c in ciks if c not in done]
    print(f"SEC: {len(ciks)} CIKs, {len(todo)} to fetch")
    lock, wlock = threading.Lock(), threading.Lock()
    last = [0.0]
    local = threading.local()

    def one(cik):
        if not hasattr(local, "s"):
            local.s = requests.Session()
            local.s.headers.update(SEC_UA)
        with lock:  # global spacing of request starts
            wait = last[0] + 1 / 7 - time.time()
            if wait > 0:
                time.sleep(wait)
            last[0] = time.time()
        r = fetch(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", local.s)
        rec = {"cik": cik}
        if r is not None:
            j = r.json()
            rec.update({k: j.get(k) for k in ("name", "sic", "sicDescription", "tickers",
                                              "exchanges", "entityType", "ownerOrg")})
        return rec

    with SEC_CACHE.open("a", encoding="utf-8") as fh, ThreadPoolExecutor(5) as ex:
        for i, rec in enumerate(ex.map(one, todo)):
            with wlock:
                fh.write(json.dumps(rec) + "\n")
            if i % 200 == 0:
                fh.flush()
                print(f"  {i}/{len(todo)}")


# ------------------------------------------------------------------ 2. CMC categories
CMC_DIR = RAW / "cmc_categories"
CMC_DIR.mkdir(exist_ok=True)
NON_SECTOR = re.compile(
    r"(etfs?$|^(cac-40|dax|dow-jones|sp500|nasdaq|ftse|nikkei)$|^(usa|china|japan|india|"
    r"united-kingdom|germany|france|canada|australia|brazil|chile|finland|hong-kong|indonesia|"
    r"israel|italy|malaysia|mexico|netherlands|new-zealand|poland|russia|saudi-arabia|singapore|"
    r"south-africa|south-korea|spain|sweden|switzerland|taiwan|thailand|turkey|vietnam|"
    r"european-union|aud|cad|eur|gbp|hkd|inr|nzd|sgd|usd|jpy|chf|cny|krw|brl|de|fr|es|it)$)")


def cmc_category_urls(s):
    cache = CMC_DIR / "_all_categories.html"
    if not cache.exists():
        r = fetch(f"{CMC}/all-categories/", s)
        cache.write_bytes(r.content)
    html = cache.read_text(encoding="utf-8", errors="replace")
    out = {}
    for path in re.findall(r'href="/([a-z0-9-]+)/([a-z0-9-]+)/"', html):
        cat, page = path
        if "by-market" not in page:
            continue
        if NON_SECTOR.search(cat):
            continue
        out[cat] = f"{CMC}/{cat}/{page}/"
    return out


SLUG_RE = re.compile(r'href="/([^"/]+)/marketcap/"')


def fetch_cmc():
    s = requests.Session()
    s.headers.update(BROWSER_UA)
    cats = cmc_category_urls(s)
    print(f"CMC: {len(cats)} sector-like categories")
    for n, (cat, url) in enumerate(sorted(cats.items())):
        out = CMC_DIR / f"{cat}.csv"
        if out.exists():
            continue
        slugs, seen = [], set()
        for page in range(1, 120):
            r = fetch(url if page == 1 else f"{url}?page={page}", s)
            time.sleep(0.8)
            if r is None:
                break
            found = [x for x in SLUG_RE.findall(r.text) if x not in seen]
            for x in found:
                seen.add(x)
                slugs.append(x)
            if len(found) < 50:  # last page (100 per page; nav may add a few)
                break
        with out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["category", "slug", "rank"])
            for i, x in enumerate(slugs, 1):
                w.writerow([cat, x, i])
        print(f"  [{n+1}/{len(cats)}] {cat}: {len(slugs)}")


# ------------------------------------------------------------------ 3. Wikidata P452
WD_CACHE = RAW / "wikidata_p452.jsonl"
WD_LABELS = RAW / "wikidata_labels.json"
WD_API = "https://www.wikidata.org/w/api.php"


def _claim_ids(claims, prop):
    out = []
    for c in claims.get(prop, []):
        v = c.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(v, dict) and "id" in v:
            out.append(v["id"])
    return out


def fetch_wikidata():
    u = load_universe()
    titles = sorted({t for t in u.wiki_title.dropna()})
    done = set()
    if WD_CACHE.exists():
        for line in WD_CACHE.open(encoding="utf-8"):
            done.add(json.loads(line)["title"])
    todo = [t for t in titles if t not in done]
    print(f"Wikidata: {len(titles)} titles, {len(todo)} to fetch")
    s = requests.Session()
    s.headers.update(WD_UA)
    with WD_CACHE.open("a", encoding="utf-8") as fh:
        for i in range(0, len(todo), 50):
            batch = todo[i:i + 50]
            r = fetch(WD_API, s, params={
                "action": "wbgetentities", "sites": "enwiki", "titles": "|".join(batch),
                "props": "claims|sitelinks", "sitefilter": "enwiki",
                "format": "json"})
            got = {}
            if r is not None:
                ents = r.json().get("entities", {})
                for qid, e in ents.items():
                    t = e.get("sitelinks", {}).get("enwiki", {}).get("title")
                    if not t or qid.startswith("-"):
                        continue
                    cl = e.get("claims", {})
                    got[t] = {"qid": qid, "p452": _claim_ids(cl, "P452"),
                              "p31": _claim_ids(cl, "P31")}
            for t in batch:
                rec = {"title": t, **got.get(t, {"qid": None, "p452": [], "p31": []})}
                fh.write(json.dumps(rec) + "\n")
            fh.flush()
            if (i // 50) % 20 == 0:
                print(f"  {i}/{len(todo)}")
            time.sleep(0.5)
    # labels for the industry items
    labels = json.loads(WD_LABELS.read_text(encoding="utf-8")) if WD_LABELS.exists() else {}
    need = set()
    for line in WD_CACHE.open(encoding="utf-8"):
        need.update(json.loads(line)["p452"])
    need = sorted(need - set(labels))
    print(f"  {len(need)} industry labels to fetch")
    for i in range(0, len(need), 50):
        r = fetch(WD_API, s, params={"action": "wbgetentities", "ids": "|".join(need[i:i + 50]),
                                     "props": "labels", "languages": "en", "format": "json"})
        if r is None:
            continue
        for qid, e in r.json().get("entities", {}).items():
            labels[qid] = e.get("labels", {}).get("en", {}).get("value", qid)
        time.sleep(0.5)
    WD_LABELS.write_text(json.dumps(labels, indent=0, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "fetch-sec":
        fetch_sec()
    elif cmd == "fetch-cmc":
        fetch_cmc()
    elif cmd == "fetch-wikidata":
        fetch_wikidata()
    elif cmd == "build":
        build()
