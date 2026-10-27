"""Second pass: Wikipedia search for companies the first pass missed.

The first pass used the query "<name> company", which fails for short names
(BMW, AXA, AT&T) and pulls wrong pages for others. This pass:
  - queries the plain cleaned name
  - accepts a hit only when the page title is close to the query string

Output is appended to wiki_descriptions.csv with a `retry` suffix on the key so
merge_profiles can prefer it.
"""

from __future__ import annotations

import csv
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
import requests

DATA = Path(__file__).resolve().parents[1] / "data"
API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "earth-atlas-research/1.0 (contact: admin@example.com)"}
SUFFIX = re.compile(r"\b(inc|corp|corporation|co|company|ltd|limited|plc|ag|sa|nv|se|spa|"
                    r"group|holding|holdings|the|pcl|nv)\b\.?", re.I)


def qn(s: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(s).lower()))


def one(company: str, key: str) -> dict:
    q = " ".join(SUFFIX.sub(" ", str(company)).split())
    rec = {"key": f"{key}::retry", "query": q, "title": None, "pageid": None,
           "extract": None, "match": False}
    for attempt in range(3):
        try:
            r = requests.get(API, params={
                "action": "query", "format": "json", "generator": "search",
                "gsrsearch": q, "gsrlimit": 1, "prop": "extracts",
                "exintro": 1, "explaintext": 1, "exlimit": 1, "redirects": 1,
            }, headers=HEADERS, timeout=25)
            pages = (r.json().get("query") or {}).get("pages", {})
            if pages:
                p = next(iter(pages.values()))
                title = p.get("title") or ""
                extract = (p.get("extract") or "").strip()
                ratio = SequenceMatcher(None, qn(q), qn(title)).ratio()
                rec.update(title=title, pageid=p.get("pageid"), extract=extract)
                rec["match"] = len(extract) > 80 and (
                    ratio > 0.8 or qn(q).startswith(qn(title)) or qn(title).startswith(qn(q)))
            return rec
        except Exception:  # noqa: BLE001
            time.sleep(1.2 * (attempt + 1))
    return rec


def main() -> None:
    profiles = pd.read_csv(DATA / "company_profiles.csv")
    profiles["has"] = profiles["description"].fillna("").str.len() > 80
    missing = profiles[(~profiles["has"]) & (profiles["revenue_usd"] > 2e9)]
    print(f"missing above $2B: {len(missing)}")

    out = DATA / "wiki_descriptions.csv"
    seen = set()
    if out.exists():
        with out.open(encoding="utf-8-sig") as fh:
            seen = {r["key"] for r in csv.DictReader(fh)}

    todo = [r for r in missing.itertuples()
            if f"{r.ticker_or_slug}::retry" not in seen]
    print(f"to retry: {len(todo)}")

    with out.open("a", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=["key", "query", "title", "pageid",
                                                "extract", "match"])
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = [pool.submit(one, r.company, r.ticker_or_slug) for r in todo]
            for fut in as_completed(futures):
                writer.writerow(fut.result())
                fh.flush()
                time.sleep(0.02)
    print("retry done")


if __name__ == "__main__":
    main()
