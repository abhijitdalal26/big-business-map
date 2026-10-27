"""Download a world map (Natural Earth 110m admin-0) for the geography charts.

Kept deliberately small and simple: country polygons keyed by ISO3 so the
map can be joined directly to the company table.  The 110m resolution is
plenty for a world map and keeps the file under a megabyte, which matters
because the dashboard embeds it.

Output: ``output/raw/world_countries.geojson``
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from config import OUT_RAW

URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
       "master/geojson/ne_110m_admin_0_countries.geojson")

# A handful of Natural Earth ISO3 codes do not match ISO 3166-1 alpha-3.
ISO_FIX = {
    "SDS": "SSD", "KOS": "XKX", "SAH": "ESH", "CYN": "CYP",
    "SOL": "SOM", "PSX": "PSE", "GRL": "GRL",
}


def main() -> Path:
    session = requests.Session()
    session.headers["User-Agent"] = "company-data-analysis/1.0 (research script)"

    print("downloading Natural Earth 110m admin-0 countries ...")
    r = session.get(URL, timeout=120)
    r.raise_for_status()
    data = r.json()

    out_features = []
    for feat in data.get("features", []):
        props = feat.get("properties", {})
        iso3 = props.get("ADM0_A3") or props.get("ISO_A3") or ""
        iso3 = ISO_FIX.get(iso3, iso3)
        if not iso3 or len(iso3) != 3:
            continue
        out_features.append({
            "type": "Feature",
            "properties": {
                "iso3": iso3,
                "name": props.get("NAME_LONG") or props.get("NAME") or iso3,
                "continent": props.get("CONTINENT", ""),
                "region_un": props.get("REGION_UN", ""),
            },
            "geometry": feat.get("geometry"),
        })

    out = {
        "type": "FeatureCollection",
        "features": out_features,
    }
    OUT_RAW.mkdir(parents=True, exist_ok=True)
    path = OUT_RAW / "world_countries.geojson"
    path.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(f"features: {len(out_features)}  size: {path.stat().st_size / 1024:.0f} KB")
    print(f"written -> {path}")
    return path


if __name__ == "__main__":
    main()
