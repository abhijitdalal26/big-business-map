"""Fortune Global 500 official list data (all 500 rows) from the Next.js
page-data JSON behind https://fortune.com/ranking/global500/.

Usage: python scripts/fetch_fortune_list.py [outdir]
Writes <outdir>/fortune_g500_list.html (the ranking page) and
<outdir>/fortune_g500_list.json (franchiseSearch items: rank, name, slug, data
with Revenues/Profits/Assets/Employees/Country/Sector/Industry...).
The list pages carry the *current* edition; check title ("Fortune Global 500 2026").
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36")


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "data/raw_2026")
    out.mkdir(parents=True, exist_ok=True)
    s = requests.Session()
    s.headers["User-Agent"] = UA
    page = s.get("https://fortune.com/ranking/global500/", timeout=60).text
    (out / "fortune_g500_list.html").write_text(page, encoding="utf-8")
    build = re.search(r'"buildId":"([^"]+)"', page).group(1)
    nd = s.get(f"https://fortune.com/_next/data/{build}/ranking/global500.json"
               "?franchiseSlug=global500", timeout=60).json()
    fs = nd["pageProps"]["franchiseSearch"]
    print(fs.get("title"), len(fs["items"]))
    (out / "fortune_g500_list.json").write_text(
        json.dumps(fs, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
