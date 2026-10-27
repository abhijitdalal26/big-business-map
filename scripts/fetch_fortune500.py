"""Build data/fortune_g500_<year>.csv from the Fortune Global 500.

Usage: python scripts/fetch_fortune500.py [year] [rawdir]   (default 2026, data/raw_2026)

Run scripts/fetch_fortune_list.py first. Revenues/profits/employees (+ country,
sector, industry, assets) come from the official ranking-list data
(fortune_g500_list.json). Company pages supply HQ, CEO, ticker, company type and
market value (the page headline block is Fortune's latest-twelve-months view and
is NOT used for revenue/profit: it differs from the ranked figures).
If no list json exists, falls back to the 2025-style slug scrape of the list HTML.

The Forbes Global 2000 only ranks *public* companies. Fortune's Global 500 is
revenue-ranked and includes state-owned enterprises and private companies that
disclose financials, so it is the natural cross-check for coverage gaps.

Output: data/fortune_g500_2025.csv
Cache : data/raw/fortune/<slug>.html
"""

from __future__ import annotations

import csv
import re
import time
from pathlib import Path

import requests
from lxml import html

import json
import sys

YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
RAW = Path(sys.argv[2] if len(sys.argv) > 2 else f"data/raw_{YEAR}")
LIST_JSON = RAW / "fortune_g500_list.json"
LIST_HTML = RAW / "fortune_g500_list.html"
CACHE = RAW / "fortune"
OUT = Path(f"data/fortune_g500_{YEAR}.csv")
BASE = "https://fortune.com/company/{slug}/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36")

FIELDS = ["Headquarters", "CEO", "Ticker", "Company type",
          "Revenues ($M)", "Profits ($M)", "Market value ($M)", "Employees"]


def list_items() -> dict[str, dict]:
    """slug -> official list item (rank, name, data)."""
    if not LIST_JSON.exists():
        return {}
    items = json.loads(LIST_JSON.read_text(encoding="utf-8"))["items"]
    return {it["slug"].strip("/").split("/")[-1]: it for it in items}


def lnum(s) -> float | None:
    m = re.match(r"^-?\d+(?:\.\d+)?", str(s or "").replace("$", "").replace(",", "").strip())
    return float(m.group(0)) if m else None


def slugs() -> list[str]:
    if LIST_JSON.exists():
        return list(list_items())
    raw = LIST_HTML.read_text(encoding="utf-8", errors="ignore")
    seen, out = set(), []
    for m in re.finditer(r"fortune\.com/company/([a-z0-9\-]+)", raw):
        s = m.group(1)
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def parse(path: Path) -> dict:
    doc = html.parse(str(path))
    root = doc.getroot()
    title = root.findtext(".//meta[@property='og:title']") or root.findtext(".//title") or ""
    h1 = root.find(".//h1")
    name = (" ".join(h1.text_content().split()) if h1 is not None else "") or \
        re.split(r"\s*[|\-]\s*", title.strip())[0].strip()
    name = re.sub(r"\s+Company Profile.*$", "", name).strip()

    vals: dict[str, str] = {}
    for li in root.iter("li"):
        t = " ".join(li.text_content().split())
        if ":" not in t or len(t) > 160:
            continue
        label, _, value = t.partition(":")
        label = label.strip()
        if label in FIELDS and label not in vals:
            vals[label] = value.strip()

    def num(s: str) -> float | None:
        s = s.replace("$", "").replace(",", "").strip()
        m = re.match(r"^-?\d+(?:\.\d+)?", s)
        return float(m.group(0)) if m else None

    return {
        "company": name,
        "slug": path.stem,
        "headquarters": vals.get("Headquarters"),
        "ceo": vals.get("CEO"),
        "company_type": vals.get("Company type"),
        "ticker": vals.get("Ticker") or None,
        "revenues_musd": num(vals.get("Revenues ($M)", "")),
        "profits_musd": num(vals.get("Profits ($M)", "")),
        "market_value_musd": num(vals.get("Market value ($M)", "")),
        "employees": num(vals.get("Employees", "")),
    }


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    all_slugs = slugs()
    official = list_items()
    print(f"slugs: {len(all_slugs)}")

    session = requests.Session()
    session.headers["User-Agent"] = UA

    rows = []
    for i, slug in enumerate(all_slugs, 1):
        path = CACHE / f"{slug}.html"
        if not path.exists():
            for attempt in range(3):
                try:
                    r = session.get(BASE.format(slug=slug), timeout=30)
                    if r.status_code == 200:
                        path.write_text(r.text, encoding="utf-8")
                        break
                except Exception as exc:  # noqa: BLE001
                    print(f"  retry {slug}: {exc}")
                time.sleep(1.5 * (attempt + 1))
            else:
                print(f"  FAILED {slug}")
                continue
            time.sleep(0.12)

        try:
            row = parse(path)
        except Exception as exc:  # noqa: BLE001
            print(f"  parse failed {slug}: {exc}")
            continue
        row["rank"] = i
        it = official.get(slug)
        if it:
            d = it["data"] if isinstance(it["data"], dict) else json.loads(it["data"])
            row["rank"] = it["rank"]
            row["company"] = it["name"]
            row["revenues_musd"] = lnum(d.get("Revenues ($M)"))
            row["profits_musd"] = lnum(d.get("Profits ($M)"))
            row["employees"] = lnum(d.get("Employees"))
            row["assets_musd"] = lnum(d.get("Assets ($M)"))
            row["country"] = d.get("Country / Territory")
            row["sector"] = d.get("Sector")
            row["industry"] = d.get("Industry")
        rows.append(row)
        if i % 50 == 0:
            print(f"  {i}/{len(all_slugs)} done")

    with OUT.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=["rank"] + [k for k in rows[0] if k != "rank"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {OUT} rows={len(rows)}")


if __name__ == "__main__":
    main()
