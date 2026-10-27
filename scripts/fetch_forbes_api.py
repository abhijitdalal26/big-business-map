"""Download Forbes list JSON from the public forbesapi endpoint.

Usage: python scripts/fetch_forbes_api.py [year] [outdir]
Writes <outdir>/<name>_<year>_api.json (same file names build_*.py read).
Lists with count 0 are reported as "no edition yet" and no file is written.
Default outdir: data/raw (use e.g. data/raw_2026 to keep editions apart).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36")
# output name -> (forbesapi list slug, limit)
LISTS = {
    "global2000": ("global2000", 2000),
    "largest_private": ("largest-private-companies", 300),
    "cloud100": ("cloud100", 200),
    "nextbillion": ("next-billion-dollar-startups", 100),
}
URL = "https://www.forbes.com/forbesapi/org/{slug}/{year}/position/true.json?limit={limit}"


def main() -> None:
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    outdir = Path(sys.argv[2] if len(sys.argv) > 2 else "data/raw")
    outdir.mkdir(parents=True, exist_ok=True)
    for name, (slug, limit) in LISTS.items():
        r = requests.get(URL.format(slug=slug, year=year, limit=limit),
                         headers={"User-Agent": UA}, timeout=120)
        n = r.json()["organizationList"]["count"] if r.status_code == 200 else 0
        if n == 0:
            print(f"{name} {year}: NO EDITION (http {r.status_code}, count 0)")
            continue
        (outdir / f"{name}_{year}_api.json").write_bytes(r.content)
        print(f"{name} {year}: {n} rows")


if __name__ == "__main__":
    main()
