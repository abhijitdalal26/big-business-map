"""Attach Wikidata facts to every company in the listed universe.

Steps
  1. Pick one English Wikipedia title per company from wiki_descriptions.csv
     (vetted titles first: the search's own `match` flag or merge_profiles'
     plausibility test; otherwise the unvetted title, which Wikidata must confirm).
  2. Resolve titles -> QIDs with wbgetentities (sites=enwiki, 50 per call);
     titles that miss (redirects) fall back to enwiki pageprops.
  3. Extract claims: P571 inception, P159 HQ, P17 country, P414 exchange (+P249
     ticker qualifier), P452 industry, P749 parent, P127 owned by, P112 founded by,
     P1128 employees (+P585 date), P1454 legal form, P31 instance of.
  4. Resolve every referenced QID to an English label in batches; HQ countries and
     "is this class a business/organisation" via the Wikidata SPARQL endpoint.
  5. Companies with no title: wbsearchentities by name for the top 3,000 by market
     cap; accept only exact (normalised) label/alias + business + country agrees.
  6. Flag likely mismatches (never delete).

Raw API responses are cached (gzipped JSON) under data/raw_wikidata/, so a re-run
is offline except for anything not yet fetched.

Output: data/universe_wikidata.csv
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
import time
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
import requests

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
RAW = DATA / "raw_wikidata"
RAW.mkdir(parents=True, exist_ok=True)

WD_API = "https://www.wikidata.org/w/api.php"
WP_API = "https://en.wikipedia.org/w/api.php"
SPARQL = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "EarthBusinessAtlas research abhijitdalal2609@gmail.com"}
MIN_INTERVAL = 0.25  # seconds between live requests (<= 4 req/s)
SEARCH_TOP_N = 3000

SESSION = requests.Session()
SESSION.headers.update(HEADERS)
_last = [0.0]


# --------------------------------------------------------------------------- http
def _cache_path(kind: str, key: str) -> Path:
    h = hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]
    return RAW / kind / f"{h}.json.gz"


def cached_get(kind: str, url: str, params: dict, method: str = "GET") -> dict:
    key = url + "?" + json.dumps(params, sort_keys=True)
    path = _cache_path(kind, key)
    if path.exists():
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    for attempt in range(6):
        wait = MIN_INTERVAL - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            if method == "POST":
                r = SESSION.post(url, data=params, timeout=90)
            else:
                r = SESSION.get(url, params=params, timeout=90)
            if r.status_code in (429, 503, 502, 504):
                time.sleep(float(r.headers.get("Retry-After", 5 * (attempt + 1))))
                continue
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict) and data.get("error", {}).get("code") == "maxlag":
                time.sleep(5)
                continue
            break
        except Exception as exc:  # noqa: BLE001
            print(f"  retry {attempt + 1} ({kind}): {exc}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    else:
        raise RuntimeError(f"failed: {kind} {key[:200]}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(data, fh)
    return data


def chunks(seq, n):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


# --------------------------------------------------------------------------- names
SUFFIX = re.compile(r"\b(inc|corp|corporation|co|company|ltd|limited|plc|ag|sa|nv|se|spa|"
                    r"group|holding|holdings|the|pcl|nv)\b\.?", re.I)
LEGAL = {"inc", "incorporated", "corp", "corporation", "co", "company", "ltd", "limited",
         "plc", "ag", "sa", "nv", "se", "spa", "pcl", "llc", "lp", "bhd", "berhad", "tbk",
         "asa", "ab", "as", "oyj", "kgaa", "gmbh", "sab", "de", "cv", "the", "publ", "pt",
         "kk", "bv", "srl", "sas", "a", "s"}

STOP = {"group", "holding", "holdings", "company", "corporation", "international",
        "industries", "the", "limited", "public"}


def tokens(s: str) -> list[str]:
    s = str(s).lower().replace("&", " and ")
    return re.findall(r"[a-z0-9]+", s)


def norm_exact(s: str) -> str:
    """Normalise for 'exact' label comparison: case, punctuation, legal suffixes."""
    return " ".join(t for t in tokens(s) if t not in LEGAL)


def plausible(query, key, title, extract) -> bool:
    """Same test merge_profiles.py uses to accept a Wikipedia hit."""
    q = str(query if isinstance(query, str) else key or "").lower()
    title = str(title or "").lower()
    extract = str(extract or "")
    if len(extract) <= 80:
        return False
    qn = " ".join(re.findall(r"[a-z0-9]+", q))
    tn = " ".join(re.findall(r"[a-z0-9]+", title))
    toks = [t for t in re.findall(r"[a-z]{4,}", q) if t not in STOP]
    if toks:
        blob = f"{title} {extract[:800]}"
        return any(t in blob for t in toks)
    if len(qn) >= 3 and (tn.startswith(qn) or qn.startswith(tn)):
        return True
    return SequenceMatcher(None, qn, tn).ratio() > 0.85


# --------------------------------------------------------------------------- countries
ALIASES = {
    "people's republic of china": "China", "prc": "China",
    "kingdom of the netherlands": "Netherlands",
    "czechia": "Czech Republic", "türkiye": "Turkey", "turkiye": "Turkey",
    "republic of ireland": "Ireland", "russian federation": "Russia",
    "republic of korea": "South Korea", "korea": "South Korea",
    "republic of china": "Taiwan", "united states of america": "United States",
    "kingdom of denmark": "Denmark", "state of palestine": "Palestine",
    "macao": "Macau", "viet nam": "Vietnam",
}
GROUPS = [
    {"China", "Hong Kong", "Macau"},
    {"United Kingdom", "Jersey", "Guernsey", "Isle of Man", "Gibraltar", "Bermuda",
     "Cayman Islands", "British Virgin Islands"},
]
# Shell/offshore domiciles: CMC country often differs from operating HQ.
OFFSHORE = {"Bermuda", "Cayman Islands", "Jersey", "Guernsey", "Isle of Man", "Bahamas",
            "British Virgin Islands", "Luxembourg", "Panama", "Gibraltar", "Monaco",
            "Liechtenstein", "Cyprus", "Ireland", "Netherlands", "Singapore"}


def canon_country(label: str | None) -> str | None:
    if not label:
        return None
    return ALIASES.get(label.lower(), label)


def country_agrees(ours: str, theirs: set[str]) -> bool:
    if not theirs:
        return False
    if ours in theirs:
        return True
    for g in GROUPS:
        if ours in g and theirs & g:
            return True
    return False


# --------------------------------------------------------------------------- claims
def _val(snak):
    if not snak or snak.get("snaktype") != "value":
        return None
    return snak["datavalue"]["value"]


def _ranked(stmts):
    """Statements in rank order, deprecated dropped; preferred only if any exist."""
    stmts = [s for s in stmts or [] if s.get("rank") != "deprecated"]
    pref = [s for s in stmts if s.get("rank") == "preferred"]
    return pref or stmts


def qids(claims, prop):
    out = []
    for s in _ranked(claims.get(prop)):
        v = _val(s.get("mainsnak"))
        if isinstance(v, dict) and v.get("id") and v["id"] not in out:
            out.append(v["id"])
    return out


def year_of(timeval: str) -> int | None:
    m = re.match(r"([+-])(\d+)-", timeval or "")
    if not m:
        return None
    y = int(m.group(2))
    return -y if m.group(1) == "-" else y


def extract_entity(ent: dict) -> dict:
    c = ent.get("claims", {}) or {}
    rec = {"qid": ent.get("id")}

    years = [year_of(_val(s["mainsnak"]).get("time")) for s in _ranked(c.get("P571"))
             if _val(s.get("mainsnak"))]
    years = [y for y in years if y is not None]
    rec["founded_year"] = min(years) if years else None

    rec["hq_q"] = qids(c, "P159")[:1]
    rec["country_q"] = qids(c, "P17")
    exch, tick = [], []
    for s in _ranked(c.get("P414")):
        v = _val(s.get("mainsnak"))
        if not isinstance(v, dict):
            continue
        t = [_val(q) for q in (s.get("qualifiers", {}) or {}).get("P249", [])]
        t = [x for x in t if isinstance(x, str)]
        exch.append(v["id"])
        tick.append(t[0] if t else "")
    rec["exch_q"], rec["exch_tick"] = exch, tick
    rec["industry_q"] = qids(c, "P452")
    rec["parent_q"] = qids(c, "P749")
    rec["owned_q"] = qids(c, "P127")
    rec["founder_q"] = qids(c, "P112")
    rec["legal_q"] = qids(c, "P1454")
    rec["p31_q"] = qids(c, "P31")

    best = (None, None)
    for s in [s for s in c.get("P1128", []) if s.get("rank") != "deprecated"]:
        v = _val(s.get("mainsnak"))
        if not isinstance(v, dict):
            continue
        try:
            n = float(v["amount"])
        except (KeyError, ValueError):
            continue
        d = [_val(q) for q in (s.get("qualifiers", {}) or {}).get("P585", [])]
        d = [x["time"][1:11] for x in d if isinstance(x, dict)]
        date = max(d) if d else ""
        rank_bonus = "~" if s.get("rank") == "preferred" and not date else ""
        cand = (rank_bonus + date, n)
        if best[0] is None or cand[0] > best[0]:
            best = cand
    rec["employees_wd"] = int(best[1]) if best[1] is not None else None
    rec["employees_wd_date"] = best[0].lstrip("~") if best[0] else None
    return rec


def fetch_entities_by_title(titles: list[str]) -> dict[str, dict]:
    """title -> extracted record (only titles with an item)."""
    out = {}
    for batch in chunks(titles, 50):
        data = cached_get("by_title", WD_API, {
            "action": "wbgetentities", "sites": "enwiki", "titles": "|".join(batch),
            "props": "claims|sitelinks", "sitefilter": "enwiki", "format": "json",
        })
        for ent in (data.get("entities") or {}).values():
            if "missing" in ent or not ent.get("id", "").startswith("Q"):
                continue
            t = ((ent.get("sitelinks") or {}).get("enwiki") or {}).get("title")
            if t:
                out[t] = extract_entity(ent)
    return out


def fetch_entities_by_id(ids: list[str]) -> dict[str, dict]:
    out = {}
    for batch in chunks(sorted(set(ids)), 50):
        data = cached_get("by_id", WD_API, {
            "action": "wbgetentities", "ids": "|".join(batch),
            "props": "claims|sitelinks|labels|aliases", "sitefilter": "enwiki",
            "languages": "en|mul", "format": "json",
        })
        for qid, ent in (data.get("entities") or {}).items():
            if "missing" in ent:
                continue
            rec = extract_entity(ent)
            rec["enwiki"] = ((ent.get("sitelinks") or {}).get("enwiki") or {}).get("title")
            names = [v["value"] for v in (ent.get("labels") or {}).values()]
            for lst in (ent.get("aliases") or {}).values():
                names += [a["value"] for a in lst]
            rec["names"] = names
            out[ent.get("id", qid)] = rec
    return out


def titles_via_pageprops(titles: list[str]) -> dict[str, str]:
    """Fallback for redirects/normalisation: enwiki title -> QID."""
    out = {}
    for batch in chunks(titles, 50):
        data = cached_get("pageprops", WP_API, {
            "action": "query", "prop": "pageprops", "ppprop": "wikibase_item",
            "redirects": "1", "titles": "|".join(batch), "format": "json",
        })
        q = data.get("query", {})
        back = {}
        for n in q.get("normalized", []):
            back[n["to"]] = n["from"]
        for r in q.get("redirects", []):
            back[r["to"]] = back.get(r["from"], r["from"])
        for p in (q.get("pages") or {}).values():
            qid = (p.get("pageprops") or {}).get("wikibase_item")
            if qid:
                orig = back.get(p["title"], p["title"])
                out[orig] = qid
    return out


def labels(ids: set[str]) -> dict[str, str]:
    out = {}
    for batch in chunks(sorted(i for i in ids if i), 50):
        data = cached_get("labels", WD_API, {
            "action": "wbgetentities", "ids": "|".join(batch), "props": "labels",
            "languages": "en|mul", "languagefallback": "1", "format": "json",
        })
        for qid, ent in (data.get("entities") or {}).items():
            lab = ent.get("labels") or {}
            v = (lab.get("en") or lab.get("mul") or next(iter(lab.values()), {})).get("value")
            out[qid] = v or qid
    return out


def sparql(query: str, kind: str) -> list[dict]:
    data = cached_get(kind, SPARQL, {"query": query, "format": "json"}, method="POST")
    return data["results"]["bindings"]


def hq_countries(hq_ids: set[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for batch in chunks(sorted(hq_ids), 300):
        vals = " ".join(f"wd:{q}" for q in batch)
        rows = sparql(f"SELECT ?x ?c WHERE {{ VALUES ?x {{ {vals} }} "
                      f"?x p:P17 ?st . ?st ps:P17 ?c . "
                      f"FILTER NOT EXISTS {{ ?st wikibase:rank wikibase:DeprecatedRank }} "
                      f"FILTER NOT EXISTS {{ ?st pq:P582 ?end }} }}", "sparql_hq")
        for r in rows:
            x = r["x"]["value"].rsplit("/", 1)[-1]
            c = r["c"]["value"].rsplit("/", 1)[-1]
            out.setdefault(x, []).append(c)
    return out


# organization (Q43229), business (Q4830453), enterprise (Q6881511), company (Q783794)
ORG_ROOTS = "wd:Q43229 wd:Q4830453 wd:Q6881511 wd:Q783794"


def org_classes(class_ids: set[str]) -> set[str]:
    out = set()
    for batch in chunks(sorted(class_ids), 60):
        vals = " ".join(f"wd:{q}" for q in batch)
        rows = sparql(f"SELECT DISTINCT ?cls WHERE {{ VALUES ?cls {{ {vals} }} "
                      f"VALUES ?root {{ {ORG_ROOTS} }} ?cls wdt:P279* ?root . }}",
                      "sparql_class")
        out |= {r["cls"]["value"].rsplit("/", 1)[-1] for r in rows}
    return out


# --------------------------------------------------------------------------- titles
def choose_titles(uni: pd.DataFrame) -> pd.DataFrame:
    wiki = pd.read_csv(DATA / "wiki_descriptions.csv")
    wiki = wiki[wiki["title"].notna()].copy()
    wiki["retry"] = wiki["key"].astype(str).str.endswith("::retry")
    wiki["base_key"] = wiki["key"].astype(str).str.split("::retry").str[0]

    # retry_wikipedia.py wrote key 'nan' for companies without a slug; recover them
    # through the cleaned query string when that is unambiguous.
    noslug = uni[uni["ticker_or_slug"].isna()]
    cleaned = noslug["company"].map(lambda c: " ".join(SUFFIX.sub(" ", str(c)).split()))
    cnt = cleaned.value_counts()
    qmap = {q: k for q, k in zip(cleaned, noslug["key"]) if cnt[q] == 1}
    bad = wiki["base_key"] == "nan"
    wiki.loc[bad, "base_key"] = wiki.loc[bad, "query"].map(qmap)
    wiki = wiki[wiki["base_key"].notna()]

    wiki["plaus"] = [plausible(q, k, t, e) for q, k, t, e in
                     zip(wiki["query"], wiki["base_key"], wiki["title"], wiki["extract"])]
    m = wiki["match"].astype(str).str.lower() == "true"
    wiki["score"] = m * 4 + wiki["plaus"] * 2 + wiki["retry"] * 1
    wiki = wiki.sort_values("score", ascending=False).drop_duplicates("base_key")
    wiki["vetted"] = (wiki["score"] >= 2)
    return wiki[["base_key", "title", "vetted"]].rename(columns={"base_key": "key"})


# --------------------------------------------------------------------------- main
def main() -> None:
    uni = pd.read_csv(DATA / "listed_universe.csv")
    uni["key"] = uni["ticker_or_slug"].fillna(uni["company"].astype(str))
    sel = choose_titles(uni)
    uni = uni.merge(sel, on="key", how="left")
    print(f"companies: {len(uni):,}; with a Wikipedia title: {uni['title'].notna().sum():,} "
          f"(vetted {uni['vetted'].fillna(False).sum():,})")

    # --- titles -> entities
    titles = sorted(set(uni["title"].dropna()))
    by_title = fetch_entities_by_title(titles)
    missing = [t for t in titles if t not in by_title]
    print(f"wbgetentities by title: {len(by_title):,} hit, {len(missing):,} missing")
    pp = titles_via_pageprops(missing)
    title_qid = {t: r["qid"] for t, r in by_title.items()}
    title_qid.update(pp)
    print(f"pageprops fallback resolved {len(pp):,}")
    ents = {r["qid"]: r for r in by_title.values()}
    ents.update(fetch_entities_by_id([q for q in pp.values() if q not in ents]))

    uni["qid"] = uni["title"].map(title_qid)
    uni["match_method"] = None
    has = uni["qid"].notna()
    uni.loc[has & uni["vetted"].fillna(False).astype(bool), "match_method"] = "enwiki_title"
    uni.loc[has & ~uni["vetted"].fillna(False).astype(bool), "match_method"] = "enwiki_title_unvetted"

    # --- search fallback for top-N by market cap without a QID
    cand_rows = uni[uni["qid"].isna()].sort_values("market_cap_usd", ascending=False)
    top_rank = uni["market_cap_usd"].rank(ascending=False, method="first")
    cand_rows = cand_rows[top_rank[cand_rows.index] <= SEARCH_TOP_N]
    print(f"search fallback candidates (top {SEARCH_TOP_N} by mcap, no QID): {len(cand_rows):,}")
    search_hits: dict[int, list[str]] = {}
    for idx, name in zip(cand_rows.index, cand_rows["company"]):
        q = " ".join(SUFFIX.sub(" ", str(name).replace("�", " ")).split()) or str(name)
        data = cached_get("search", WD_API, {
            "action": "wbsearchentities", "search": q, "language": "en", "type": "item",
            "limit": "7", "format": "json"})
        search_hits[idx] = [h["id"] for h in data.get("search", [])]
    sents = fetch_entities_by_id({q for v in search_hits.values() for q in v} - set(ents))
    ents.update(sents)

    # --- class check and labels need all candidate P31s first
    all_p31 = {c for r in ents.values() for c in r["p31_q"]}
    orgc = org_classes(all_p31)
    is_biz = lambda r: bool(set(r["p31_q"]) & orgc)  # noqa: E731

    hq_ids = {q for r in ents.values() for q in r["hq_q"]}
    hqc = hq_countries(hq_ids)
    lab_ids = set(all_p31) | hq_ids | {c for v in hqc.values() for c in v}
    for r in ents.values():
        for k in ("country_q", "exch_q", "industry_q", "parent_q", "owned_q",
                  "founder_q", "legal_q"):
            lab_ids |= set(r[k])
    L = labels(lab_ids)
    print(f"labels resolved: {len(L):,}")

    def wd_countries(r) -> set[str]:
        cs = {canon_country(L.get(c)) for c in r["country_q"]}
        for h in r["hq_q"]:
            cs |= {canon_country(L.get(c)) for c in hqc.get(h, [])}
        return {c for c in cs if c}

    accepted = 0
    for idx, hits in search_hits.items():
        ours = uni.at[idx, "country"]
        target = norm_exact(uni.at[idx, "company"])
        for q in hits:
            r = ents.get(q)
            if not r or not target:
                continue
            if target not in {norm_exact(n) for n in r.get("names", [])}:
                continue
            if is_biz(r) and country_agrees(ours, wd_countries(r)):
                uni.at[idx, "qid"] = q
                uni.at[idx, "match_method"] = "wd_search_exact"
                accepted += 1
                break
    print(f"search fallback accepted: {accepted:,}")

    # --- assemble
    def lab_list(qs, n=None):
        qs = qs[:n] if n else qs
        return "; ".join(L.get(q, q) for q in qs) or None

    rows = []
    for _, u in uni.iterrows():
        r = ents.get(u["qid"]) if isinstance(u["qid"], str) else None
        base = {"company": u["company"], "ticker_or_slug": u["ticker_or_slug"],
                "qid": u["qid"] if r else None,
                "match_method": u["match_method"] if r else None}
        if not r:
            rows.append(base | {"wiki_title": u["title"]})
            continue
        flags = []
        biz = is_biz(r)
        if not biz:
            flags.append("not_business")
        wdc = wd_countries(r)
        ours = u["country"]
        if not wdc:
            flags.append("no_country_wd")
        elif not country_agrees(ours, wdc):
            flags.append("country_mismatch_offshore" if ours in OFFSHORE
                         else "country_mismatch")
        if u["match_method"] == "enwiki_title_unvetted" and (flags or not biz):
            flags.append("unvetted_title")
        hq = r["hq_q"][0] if r["hq_q"] else None
        hq_country = None
        if hq and hqc.get(hq):
            hq_country = canon_country(L.get(hqc[hq][0]))
        elif r["country_q"]:
            hq_country = canon_country(L.get(r["country_q"][0]))
        exch = [L.get(e, e) for e in r["exch_q"]]
        tick = [f"{L.get(e, e)}:{t}" for e, t in zip(r["exch_q"], r["exch_tick"]) if t]
        rows.append(base | {
            "match_flag": ";".join(flags) or None,
            "founded_year": r["founded_year"],
            "hq_city": L.get(hq) if hq else None,
            "hq_country": hq_country,
            "exchanges": "; ".join(dict.fromkeys(exch)) or None,
            "industry_wd": lab_list(r["industry_q"]),
            "parent": lab_list(r["parent_q"]),
            "owned_by": lab_list(r["owned_q"], 8),
            "founded_by": lab_list(r["founder_q"], 8),
            "employees_wd": r["employees_wd"],
            "employees_wd_date": r["employees_wd_date"],
            "legal_form": lab_list(r["legal_q"]),
            "tickers_wd": "; ".join(dict.fromkeys(tick)) or None,
            "country_wd": "; ".join(sorted(wdc)) or None,
            "instance_of": lab_list(r["p31_q"], 5),
            "wiki_title": u["title"] if u["match_method"] != "wd_search_exact"
            else r.get("enwiki"),
        })

    cols = ["company", "ticker_or_slug", "qid", "match_method", "match_flag",
            "founded_year", "hq_city", "hq_country", "exchanges", "industry_wd", "parent",
            "owned_by", "founded_by", "employees_wd", "employees_wd_date", "legal_form",
            "tickers_wd", "country_wd", "instance_of", "wiki_title"]
    out = pd.DataFrame(rows).reindex(columns=cols)
    out["founded_year"] = out["founded_year"].astype("Int64")
    out["employees_wd"] = out["employees_wd"].astype("Int64")
    out.to_csv(DATA / "universe_wikidata.csv", index=False, encoding="utf-8-sig")

    # --- summary
    mc = uni["market_cap_usd"].fillna(0)
    got = out["qid"].notna()
    print(f"\nrows {len(out):,}; with QID {got.sum():,} ({got.mean():.1%}); "
          f"mcap share {mc[got.values].sum() / mc.sum():.1%}")
    print(out["match_method"].value_counts(dropna=False).to_string())
    print(out["match_flag"].fillna("ok").str.split(";").explode().value_counts().to_string())
    for c in cols[5:16]:
        print(f"  {c:18s} {out.loc[got, c].notna().mean():6.1%} of matched")


if __name__ == "__main__":
    main()
