"""Fetch a one-sentence Wikipedia description for companies in
article/data/business_ideas.csv that have no description yet.

Caches to article/data/wiki_ideas.csv so it only ever asks once per company.
A match is kept only if the sentence looks like it describes a business.
Run from the repo root:  python article/fetch_wiki_ideas.py
"""

from __future__ import annotations

import re
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "article/data/wiki_ideas.csv"
API = "https://en.wikipedia.org/w/api.php"
HEAD = {"User-Agent": "big-business-map research (github.com/abhijitdalal26)"}
BUSINESSY = re.compile(r"\b(company|companies|corporation|conglomerate|group|firm|enterprise|"
                       r"cooperative|co-operative|insurer|bank|retailer|manufacturer|operator|"
                       r"utility|producer|business|chain|partnership|holding|supermarket|"
                       r"provider|trader|distributor|maker|multinational|insurance)\b", re.I)


def get(params: dict) -> dict:
    """GET with back-off: Wikipedia answers bursts with an HTML 429 page."""
    for wait in (2, 5, 15, 30, 60):
        r = requests.get(API, params=params, headers=HEAD, timeout=20)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/json"):
            return r.json()
        time.sleep(wait)
    raise RuntimeError(f"gave up after retries (HTTP {r.status_code})")


def lookup(name: str) -> tuple[str, str]:
    q = re.sub(r"\s+", " ", name).strip()
    hits = get({"action": "query", "list": "search", "srsearch": f"{q} company",
                "format": "json", "srlimit": 1}).get("query", {}).get("search", [])
    if not hits:
        return "", ""
    title = hits[0]["title"]
    data = get({"action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1,
                "exsentences": 1, "titles": title, "format": "json", "redirects": 1})
    page = next(iter(data["query"]["pages"].values()))
    text = page.get("extract", "") or ""
    return title, text if BUSINESSY.search(text) else ""


def main() -> None:
    c = pd.read_csv(ROOT / "article/data/business_ideas.csv")
    todo = c[c.what_they_do.isna()].company.str.strip().unique().tolist()
    done = pd.read_csv(CACHE) if CACHE.exists() else pd.DataFrame(columns=["company", "title", "extract"])
    todo = [n for n in todo if n not in set(done.company)]
    print(len(todo), "to fetch")
    rows = []
    for i, name in enumerate(todo, 1):
        try:
            title, text = lookup(name)
        except Exception as e:  # network hiccup: skip, retry next run
            print("fail", name, e)
            continue
        rows.append({"company": name, "title": title, "extract": text})
        if i % 50 == 0:
            print(i, flush=True)
        time.sleep(1.0)
    pd.concat([done, pd.DataFrame(rows)]).to_csv(CACHE, index=False)
    print("cached", len(rows))


if __name__ == "__main__":
    main()
