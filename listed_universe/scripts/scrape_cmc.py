"""Global listed companies from companiesmarketcap.com (estimate-grade).

Two stages so the expensive part can run in the background:
  1. list pages  -> rank, name, ticker, market cap, country
  2. revenue pages (optional, --revenue N) -> TTM revenue per company

robots.txt of the site disallows only report-download paths, not these pages.
Requests are throttled and results are checkpointed, so the job is resumable.

Outputs:
  listed_universe/data/cmc_list.csv
  listed_universe/data/cmc_revenue.csv   (if stage 2 ran)
"""

from __future__ import annotations

import argparse
import csv
import re
import time
from pathlib import Path

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
}
BASE = "https://companiesmarketcap.com"
OUT = Path(__file__).resolve().parents[1] / "data"

ROW_RE = re.compile(
    r'<td class="rank-td td-right" data-sort="(?P<rank>\d+)">'
    r'.*?<div class="company-name">(?P<name>[^<]+)</div>'
    r'<div class="company-code">.*?</div>'
    r'.*?href="/(?P<slug>[^/"]+)/marketcap/"'
    r'.*?<td class="td-right" data-sort="(?P<mcap>\d+)">'
    r'.*?<td><img class="flag" src="/img/flags/(?P<cc>[a-z]{2})\.png">\s*'
    r'<span class="responsive-hidden">(?P<country>[^<]*)</span>',
    re.S,
)
REV_RE = re.compile(
    r"Revenue in (?P<year>\d{4})(?: \(TTM\))?:\s*<span[^>]*>\$(?P<val>[\d.,]+)\s*(?P<unit>Billion|Million|Trillion) USD"
)

UNIT = {"Billion": 1e9, "Million": 1e6, "Trillion": 1e12}


def fetch(url: str, session: requests.Session, tries: int = 3):
    for i in range(tries):
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 200:
                return r.content
            if r.status_code == 404:
                return None
        except Exception as exc:  # noqa: BLE001
            print(f"    retry {url}: {exc}")
        time.sleep(1.0 * (i + 1))
    return None


def stage_list(session: requests.Session, pages: int) -> list[dict]:
    from lxml import html as lhtml

    rows: list[dict] = []
    for p in range(1, pages + 1):
        raw = fetch(f"{BASE}/?page={p}", session)
        if not raw:
            print(f"  page {p}: empty/failed")
            continue
        doc = lhtml.fromstring(raw if isinstance(raw, bytes) else raw.encode())
        trs = doc.xpath("//table[contains(@class,'marketcap-table')]//tbody/tr")
        found = 0
        for tr in trs:
            tds = tr.xpath("./td")
            if len(tds) < 4:
                continue
            names = tr.xpath(".//div[@class='company-name']")
            hrefs = tr.xpath(".//a/@href")
            if not names or not hrefs:
                continue
            slug = hrefs[0].strip("/").split("/")[0]
            code_div = tr.xpath(".//div[@class='company-code']")
            ticker = " ".join(code_div[0].text_content().split()) if code_div else None
            ticker = ticker or None
            mcap = tds[3].get("data-sort")
            country = " ".join(tr.xpath("./td[last()]//span")[-1].text_content().split()) \
                if tr.xpath("./td[last()]//span") else None
            rows.append({
                "rank": tds[1].text_content().strip(),
                "name": " ".join(names[0].text_content().split()),
                "slug": slug,
                "ticker": ticker,
                "market_cap_usd": float(mcap) if mcap else None,
                "cc": None,
                "country": country,
            })
            found += 1
        print(f"  page {p}: {found} rows (total {len(rows)})")
        time.sleep(0.2)
    return rows


def stage_revenue(session: requests.Session, rows: list[dict], n: int) -> None:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    path = OUT / "cmc_revenue.csv"
    done: set[str] = set()
    if path.exists():
        with path.open(encoding="utf-8-sig") as fh:
            done = {r["slug"] for r in csv.DictReader(fh)}
    todo = [r for r in rows[:n] if r["slug"] not in done]
    print(f"revenue stage: {len(todo)} to fetch ({len(done)} cached)")

    def one(row: dict) -> dict:
        h = fetch(f"{BASE}/{row['slug']}/revenue/", session)
        rec = {"slug": row["slug"], "name": row["name"], "revenue_usd": None,
               "revenue_period": None}
        if h:
            h = h.decode("utf-8", errors="replace") if isinstance(h, bytes) else h
            m = REV_RE.search(h)
            if m:
                rec["revenue_usd"] = float(m.group("val").replace(",", "")) * UNIT[m.group("unit")]
                rec["revenue_period"] = m.group("year")
        return rec

    with path.open("a", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=["slug", "name", "revenue_usd", "revenue_period"])
        if not done:
            writer.writeheader()
        worker = requests.Session()
        worker.headers.update(HEADERS)
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(one, r) for r in todo]
            for i, fut in enumerate(as_completed(futures), 1):
                writer.writerow(fut.result())
                fh.flush()
                if i % 200 == 0:
                    print(f"  revenue {i}/{len(todo)}")
                time.sleep(0.05)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=60, help="list pages (100 companies each)")
    ap.add_argument("--revenue", type=int, default=0, help="fetch TTM revenue for the top N")
    ap.add_argument("--resume-list", action="store_true")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update(HEADERS)

    list_path = OUT / "cmc_list.csv"
    if args.resume_list and list_path.exists():
        rows = list(csv.DictReader(list_path.open(encoding="utf-8-sig")))
    else:
        rows = stage_list(session, args.pages)
        with list_path.open("w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=["rank", "name", "slug", "ticker", "market_cap_usd", "cc", "country"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {list_path} rows={len(rows)}")

    if args.revenue:
        stage_revenue(session, rows, args.revenue)
        print("revenue stage complete")


if __name__ == "__main__":
    main()
