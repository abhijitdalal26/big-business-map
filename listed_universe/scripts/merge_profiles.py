"""Attach 'what this company does' text to the listed universe.

Priority:
  1. Forbes description (for the 2,000 atlas companies, ~700 chars, editorial)
  2. Wikipedia intro (fetched for every company, CC BY-SA)
  3. none

Output: listed_universe/data/company_profiles.csv
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
ATLAS = BASE.parent / "data"


def norm(name: str) -> str:
    s = str(name).lower().replace("&", " and ")
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return " ".join(s.split())


def main() -> None:
    uni = pd.read_csv(DATA / "listed_universe.csv")
    uni["key"] = uni["ticker_or_slug"].fillna(uni["company"].astype(str))

    STOP = {"group", "holding", "holdings", "company", "corporation", "international",
            "industries", "the", "limited", "public"}

    def plausible(row) -> bool:
        from difflib import SequenceMatcher
        q = str(row["query"] or row["key"] or "").lower()
        title = str(row["title"] or "").lower()
        extract = str(row["extract"] or "")
        if len(extract) <= 80:
            return False
        qn = " ".join(re.findall(r"[a-z0-9]+", q))
        tn = " ".join(re.findall(r"[a-z0-9]+", title))
        tokens = [t for t in re.findall(r"[a-z]{4,}", q) if t not in STOP]
        if tokens:
            blob = f"{title} {extract[:800]}"
            return any(t in blob for t in tokens)
        if len(qn) >= 3 and (tn.startswith(qn) or qn.startswith(tn)):
            return True
        return SequenceMatcher(None, qn, tn).ratio() > 0.85

    wiki = pd.read_csv(DATA / "wiki_descriptions.csv")
    wiki["extract"] = wiki["extract"].fillna("").str.strip()
    wiki = wiki[wiki.apply(plausible, axis=1)].copy()
    wiki["base_key"] = wiki["key"].astype(str).str.split("::retry").str[0]
    wiki = wiki.drop_duplicates("base_key", keep="last")
    wiki["key"] = wiki["base_key"]
    wiki_map = dict(zip(wiki["key"], wiki["extract"]))
    title_map = dict(zip(wiki["key"], wiki["title"]))

    desc = uni["key"].map(wiki_map)
    source = desc.notna().map({True: "Wikipedia (CC BY-SA)", False: None})
    titles = uni["key"].map(title_map)

    # overlay Forbes editorial descriptions where the names match exactly
    fpath = ATLAS / "global2000_2025.csv"
    if fpath.exists():
        forbes = pd.read_csv(fpath)[["company", "description"]]
        forbes = forbes[forbes["description"].fillna("").str.len() > 50]
        fmap = {norm(c): d for c, d in zip(forbes["company"], forbes["description"])}
        fdesc = uni["company"].map(lambda c: fmap.get(norm(c)))
        take = fdesc.notna()
        desc = desc.where(~take, fdesc)
        source = source.where(~take, "Forbes")

    out = pd.DataFrame({
        "company": uni["company"],
        "ticker_or_slug": uni["ticker_or_slug"],
        "country": uni["country"],
        "revenue_usd": uni["revenue_usd"],
        "market_cap_usd": uni["market_cap_usd"],
        "confidence": uni["confidence"],
        "description": desc,
        "description_source": source,
        "wiki_title": titles,
    }).sort_values("revenue_usd", ascending=False, na_position="last")

    out.to_csv(DATA / "company_profiles.csv", index=False, encoding="utf-8-sig")

    print(f"rows: {len(out):,}")
    print(out["description_source"].value_counts(dropna=False).to_string())
    have = out["description"].fillna("").str.len() > 80
    print(f"with description: {have.sum():,} ({have.mean()*100:.1f}%)")
    big = out[out["revenue_usd"] > 1e9]
    print(f"$1B+ companies with description: "
          f"{(big['description'].fillna('').str.len() > 80).sum():,} of {len(big):,}")
    print(out[out["revenue_usd"] > 1e11][["company", "description"]].head(5).to_string(index=False))


if __name__ == "__main__":
    main()
