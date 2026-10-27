"""Enrich the AI companies table with:
  - a description of what each company is building (Wikipedia intro)
  - Wikipedia URL as a citation
  - investors + valuation + valuation date from the CB Insights unicorn board
  - a total_funding_usd column that stays EMPTY unless verified (no invented numbers)

Output: ai_labs/data/ai_companies.csv (rewritten with new columns)
"""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "earth-atlas-research/1.0 (contact: admin@example.com)"}

STOP = {"inc", "corp", "corporation", "co", "ltd", "limited", "plc", "technologies",
        "technology", "labs", "ai", "the", "group", "systems", "research"}


def wiki(company: str) -> dict:
    q = re.sub(r"\s*\(.*?\)", "", str(company))
    q = " ".join(q.split())
    out = {"description": None, "description_source": None, "wiki_url": None,
           "wiki_title": None}
    for attempt in range(3):
        try:
            r = requests.get(API, params={
                "action": "query", "format": "json", "generator": "search",
                "gsrsearch": f"{q} company AI", "gsrlimit": 1,
                "prop": "extracts|info", "inprop": "url",
                "exintro": 1, "explaintext": 1, "exlimit": 1, "redirects": 1,
            }, headers=HEADERS, timeout=25)
            pages = (r.json().get("query") or {}).get("pages", {})
            if not pages:
                return out
            p = next(iter(pages.values()))
            extract = (p.get("extract") or "").strip()
            title = p.get("title") or ""
            toks = [t for t in re.findall(r"[a-z]{3,}", q.lower()) if t not in STOP]
            blob = f"{title} {extract[:500]}".lower()
            if len(extract) > 80 and (not toks or any(t in blob for t in toks)):
                out.update(description=extract, description_source="Wikipedia (CC BY-SA)",
                           wiki_title=title,
                           wiki_url=p.get("fullurl"))
            return out
        except Exception:  # noqa: BLE001
            time.sleep(1.2 * (attempt + 1))
    return out


def main() -> None:
    df = pd.read_csv(DATA / "ai_companies.csv")

    # --- CB Insights join: valuation, investors, date ---
    uni_path = BASE.parent / "startups" / "data" / "startups_global.csv"
    cb = pd.read_csv(uni_path) if uni_path.exists() else pd.DataFrame()
    if not cb.empty:
        cb["k"] = cb["company"].str.lower()
        cmap = cb.drop_duplicates("k").set_index("k")
        df["valuation_busd_cb"] = df["company"].str.lower().map(cmap["valuation_busd"])
        df["investors"] = df["company"].str.lower().map(cmap["investors"])
        df["valuation_date"] = df["company"].str.lower().map(cmap["date_joined"])

    # --- descriptions ---
    todo = [c for c in df["company"].unique()]
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(wiki, c): c for c in todo}
        for i, fut in enumerate(as_completed(futures), 1):
            results[futures[fut]] = fut.result()
            if i % 50 == 0:
                print(f"  descriptions {i}/{len(todo)}")

    desc = df["company"].map(lambda c: results.get(c, {}).get("description"))
    src = df["company"].map(lambda c: results.get(c, {}).get("description_source"))
    url = df["company"].map(lambda c: results.get(c, {}).get("wiki_url"))
    title = df["company"].map(lambda c: results.get(c, {}).get("wiki_title"))

    df["description"] = desc
    df["description_source"] = src
    df["wiki_url"] = url
    df["wiki_title"] = title

    # funding: never invented
    df["total_funding_usd"] = None
    df["funding_source"] = None

    cols = ["company", "modality", "category", "country", "founded", "status",
            "parent", "open_weights", "hf_org", "ticker", "valuation_busd_cb",
            "valuation_date", "investors", "total_funding_usd", "funding_source",
            "description", "description_source", "wiki_url"]
    df = df[cols]
    df.to_csv(DATA / "ai_companies.csv", index=False, encoding="utf-8-sig")

    have = df["description"].fillna("").str.len() > 80
    print(f"\ncompanies: {len(df)}")
    print(f"with description: {have.sum()} ({have.mean()*100:.1f}%)")
    print(f"with valuation: {df.valuation_busd_cb.notna().sum()}")
    print(f"with investors: {df.investors.notna().sum()}")
    print("\nsample:")
    print(df[have].head(3)[["company", "description"]].to_string(index=False))


if __name__ == "__main__":
    main()
