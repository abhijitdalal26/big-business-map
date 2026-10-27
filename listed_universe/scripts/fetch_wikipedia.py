"""Fetch a one-paragraph 'what this company does' from Wikipedia for every company
in the listed universe.

Free, no API key, CC BY-SA licensed (attribute Wikipedia in the article).

Matching: search "<name> company", take the top hit, accept it only if the page
title or extract plausibly refers to that company. Results are checkpointed and
the job is resumable.

Output: listed_universe/data/wiki_descriptions.csv
"""

from __future__ import annotations

import csv
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

DATA = Path(__file__).resolve().parents[1] / "data"
OUT = DATA / "wiki_descriptions.csv"
API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "earth-atlas-research/1.0 (contact: admin@example.com)"}

SUFFIX = re.compile(
    r"\b(inc|corp|corporation|co|company|ltd|limited|plc|ag|sa|nv|se|spa|"
    r"group|holding|holdings|the)\b\.?", re.I)


def clean(name: str) -> str:
    s = SUFFIX.sub(" ", str(name))
    return " ".join(s.replace("&", "and").split())


def one(row: dict) -> dict:
    q = clean(row["company"])
    rec = {"key": row["key"], "query": q, "title": None, "pageid": None,
           "extract": None, "match": False}
    if not q:
        return rec
    for attempt in range(3):
        try:
            r = requests.get(API, params={
                "action": "query", "format": "json", "generator": "search",
                "gsrsearch": f"{q} company", "gsrlimit": 1,
                "prop": "extracts", "exintro": 1, "explaintext": 1,
                "exlimit": 1, "redirects": 1,
            }, headers=HEADERS, timeout=25)
            data = r.json()
            pages = (data.get("query") or {}).get("pages", {})
            if pages:
                p = next(iter(pages.values()))
                extract = (p.get("extract") or "").strip()
                title = p.get("title")
                rec.update(title=title, pageid=p.get("pageid"), extract=extract)
                first = q.split()[0].lower()
                blob = f"{title} {extract[:400]}".lower()
                rec["match"] = len(extract) > 80 and first in blob
            return rec
        except Exception:  # noqa: BLE001
            time.sleep(1.2 * (attempt + 1))
    return rec


def main() -> None:
    uni = pd.read_csv(DATA / "listed_universe.csv")
    uni["key"] = uni["ticker_or_slug"].fillna(uni["company"].astype(str))
    rows = uni[["key", "company"]].drop_duplicates("key").to_dict("records")

    done: set[str] = set()
    if OUT.exists():
        with OUT.open(encoding="utf-8-sig") as fh:
            done = {r["key"] for r in csv.DictReader(fh)}
    todo = [r for r in rows if r["key"] not in done]
    print(f"{len(rows)} companies, {len(done)} cached, {len(todo)} to fetch")

    with OUT.open("a", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=["key", "query", "title", "pageid",
                                                "extract", "match"])
        if not done:
            writer.writeheader()
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(one, r): r for r in todo}
            for i, fut in enumerate(as_completed(futures), 1):
                writer.writerow(fut.result())
                fh.flush()
                if i % 250 == 0:
                    print(f"  {i}/{len(todo)}")
                time.sleep(0.02)
    print("done")


if __name__ == "__main__":
    main()
