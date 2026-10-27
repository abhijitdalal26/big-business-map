"""Build site/assets/world.geo.js from a Natural Earth 1:50m admin-0 GeoJSON.

Usage: python site/build/world_geo.py <path to ne_50m_admin_0_countries.geojson>
Source: https://github.com/nvkelso/natural-earth-vector (public domain).
Each feature's properties.name is set to its ISO3 code so data can be keyed by ISO3;
properties.label keeps the English name. Coordinates are rounded to 2 decimals.
"""
import json, sys, os

src = sys.argv[1]
out = os.path.join(os.path.dirname(__file__), '..', 'assets', 'world.geo.js')
g = json.load(open(src, encoding='utf-8'))
FIX = {'KOS': 'XKX', 'SDS': 'SSD', 'PSX': 'PSE', 'SAH': 'ESH'}

def clean_ring(ring, nd=2):
    outr, last = [], None
    for x, y in ring:
        p = (round(x, nd), round(y, nd))
        if p != last:
            outr.append(list(p)); last = p
    return outr if len(outr) >= 4 else None

def ring_area(r):
    return abs(sum(r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1] for i in range(len(r) - 1))) / 2

feats = []
for f in g['features']:
    p = f['properties']
    iso = p.get('ISO_A3')
    if not iso or iso == '-99':
        iso = p.get('ADM0_A3')
    iso = FIX.get(iso, iso)
    if iso == 'ATA':
        continue  # Antarctica wastes space on a business map
    geom = f['geometry']
    polys = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
    newp = []
    for poly in polys:
        rings = [clean_ring(r) for r in poly]
        if rings[0] is None:
            continue
        # drop tiny islands (<0.02 sq deg) unless it's the only polygon of the country
        if len(polys) > 1 and ring_area(rings[0]) < 0.02:
            continue
        newp.append([r for r in rings if r])
    if not newp:
        continue
    feats.append({'type': 'Feature', 'properties': {'name': iso, 'label': p.get('NAME_EN') or p.get('NAME')},
                  'geometry': {'type': 'MultiPolygon', 'coordinates': newp}})

fc = {'type': 'FeatureCollection', 'features': feats}
with open(out, 'w', encoding='utf-8') as fh:
    fh.write('/* Natural Earth 1:50m admin-0 countries (public domain), simplified. properties.name = ISO3. */\n')
    fh.write('window.WORLD_GEO=' + json.dumps(fc, separators=(',', ':'), ensure_ascii=False) + ';\n')
print(len(feats), 'features ->', out, os.path.getsize(out) // 1024, 'KB')
