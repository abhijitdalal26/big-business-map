"""Build site/data/market_history.js  ->  window.ATLAS.marketHistory = {...}

Inputs (from stock_market/scripts/fetch_history.py):
  stock_market/data/index_monthly.csv   main stock index per country, month-end close (Yahoo Finance)
  stock_market/data/fx_monthly.csv      local currency per US$, monthly average (FRED; Yahoo for IDR/ARS/ILS/TRY)
  stock_market/data/wb_market_history.csv  World Bank market cap, US$ and % of GDP, 1975-2025
Run:  python site/build/market_history.py
"""
import json, math
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'site' / 'data' / 'market_history.js'
SM = ROOT / 'stock_market' / 'data'

# World Bank points that are reporting errors, not market moves. Each is dropped and listed on the page.
DROP_POINTS = {
    ('IND', 2018): 'NSE and BSE totals added together (double count): $4.1T, 153% of GDP, then $2.2T in 2019',
    ('IND', 2025): 'NSE and BSE totals added together (double count): $10.6T, 267% of GDP, vs ~$5T actual',
    ('WLD', 2025): 'world total includes the India 2025 double count (about $5T too high)',
    ('ITA', 1998): 'value of $0.3B, about 1,000x too small (data entry error)',
    ('FRA', 1998): 'value of $151B between $674B (1997) and $1.5T (1999), a data error',
    ('BGD', 2025): 'listed companies halve and value falls 70% in one year: a series break',
}
DROP_COUNTRIES = {
    'IRN': 'converted at the official exchange rate, so US$ values swing from $0.1T to $2T and back',
    'AZE': 'a handful of tiny data points with a 950-company jump in 2019',
}
NAMES = {'WLD': 'World', 'KOR': 'South Korea', 'HKG': 'Hong Kong', 'RUS': 'Russia', 'IRN': 'Iran', 'EGY': 'Egypt', 'TUR': 'Turkey', 'VEN': 'Venezuela', 'SVK': 'Slovakia', 'KGZ': 'Kyrgyzstan', 'LAO': 'Laos', 'MAC': 'Macao', 'CZE': 'Czech Republic'}
EURO_LEGACY = {'Germany', 'France', 'Netherlands', 'Spain', 'Italy'}


def r(v, d=2):
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else round(float(v), d)


FX_DROPPED = []


def despike_fx(cur, s):
    """Yahoo FX has broken months, sometimes several in a row (rupiah at ~1 per US$ instead of ~14,000).
    Drop any month more than 50% away from the median of the 13 months around it. A real devaluation
    is a lasting step, and the median follows it within a month or two, so it is kept."""
    ms = sorted(s)
    vals = [s[m] for m in ms]
    bad = []
    for i, m in enumerate(ms):
        win = sorted(vals[max(0, i - 6): i + 7])
        med = win[len(win) // 2]
        if not (med / 1.5 < vals[i] < med * 1.5):
            bad.append(m)
    FX_DROPPED.extend(f'{cur} {m}' for m in bad)
    return {m: v for m, v in s.items() if m not in bad}


def spikes(g, iso, name, log):
    """Rows in a run of 1-2 years that sit more than 3x away from BOTH the year before and the year after
    (Japan 1977-78 at 3% of GDP between 30% and 26%, Norway 1984 at 94% between 7% and 15%).
    Real crashes and booms do not snap back inside two years like that. Returns the row labels to drop."""
    v, y, bad = g.mcap_usd.tolist(), g.year.tolist(), []
    for i in range(1, len(v) - 1):
        for run in (1, 2):
            j = i + run  # first row after the run
            if j >= len(v) or y[j] - y[i - 1] > run + 1 or any(k in bad for k in range(i, j)):
                continue
            seg = v[i:j]
            lo = all(s < v[i - 1] / 3 and s < v[j] / 3 for s in seg)
            hi = all(s > v[i - 1] * 3 and s > v[j] * 3 for s in seg)
            if lo or hi:
                for k in range(i, j):
                    bad.append(k)
                    log.append({'iso': iso, 'year': int(y[k]), 'why': f'{name}: ${v[k] / 1e9:,.1f}B between ${v[i - 1] / 1e9:,.1f}B '
                                f'({y[i - 1]}) and ${v[j] / 1e9:,.1f}B ({y[j]}), a reporting error'})
                break
    return bad


def months(a, b):
    y, m = map(int, a.split('-')); y2, m2 = map(int, b.split('-'))
    out = []
    while (y, m) <= (y2, m2):
        out.append(f'{y}-{m:02d}'); m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def main():
    idx = pd.read_csv(SM / 'index_monthly.csv')
    fx = pd.read_csv(SM / 'fx_monthly.csv')
    fxd = {c: despike_fx(c, dict(zip(g.month, g.local_per_usd))) for c, g in fx.groupby('currency')}

    indexes = []
    for (country, name, sym, cur), g in idx.groupby(['country', 'index', 'symbol', 'currency'], sort=False):
        s = dict(zip(g.month, g.close))
        ms = months(min(s), max(s))
        loc = [s.get(m) for m in ms]
        usd, last_fx, stale = [], None, 0
        for m, v in zip(ms, loc):
            if cur == 'USD':
                rate = 1.0
            else:
                key = 'EUR:' + country if cur == 'EUR' and country in EURO_LEGACY and m < '1999-01' else cur
                rate = fxd.get(key, {}).get(m)
                # carry the last rate forward at most 2 months (FRED publishes with a lag)
                if rate is None and last_fx is not None and stale < 2:
                    rate, stale = last_fx, stale + 1
                elif rate is not None:
                    last_fx, stale = rate, 0
            usd.append(None if v is None or rate is None else v / rate)
        indexes.append({'country': country, 'name': name, 'symbol': sym, 'cur': cur, 'start': ms[0],
                        'loc': [r(v, 2) for v in loc], 'usd': [r(v, 4) for v in usd]})
    print('indexes', len(indexes), '| FX months dropped as glitches:', len(FX_DROPPED), FX_DROPPED[:8])

    w = pd.read_csv(SM / 'wb_market_history.csv')
    meta = pd.read_csv(ROOT / 'data' / 'country_meta.csv', encoding='utf-8-sig')
    region = {k: str(v).strip() for k, v in zip(meta.iso3, meta.region)}
    countries, auto = [], []
    for (iso, name), g in w.groupby(['iso3', 'country']):
        if iso != 'WLD' and iso not in region:
            continue  # aggregates such as "High income"
        if iso in DROP_COUNTRIES:
            continue
        g = g[[(iso, y) not in DROP_POINTS for y in g.year]]
        g = g.dropna(subset=['mcap_usd']).reset_index(drop=True)
        g = g.drop(index=spikes(g, iso, NAMES.get(iso, name), auto))
        if len(g) < 5:
            continue
        countries.append({'iso': iso, 'name': NAMES.get(iso, name), 'region': region.get(iso, 'World'),
                          'mcap': {int(y): r(v, 0) for y, v in zip(g.year, g.mcap_usd)},
                          'pct': {int(y): r(v, 1) for y, v in zip(g.year, g.mcap_pct_gdp) if not pd.isna(v)}})
    countries.sort(key=lambda c: -(c['mcap'].get(max(c['mcap'])) or 0))
    print('wb countries', len(countries))

    data = {'indexes': indexes, 'wb': countries,
            'dropped_points': [{'iso': k[0], 'year': k[1], 'why': v} for k, v in DROP_POINTS.items()] + auto,
            'dropped_countries': [{'iso': k, 'why': v} for k, v in DROP_COUNTRIES.items()],
            'last_month': max(idx.month)}
    OUT.write_text('/* generated by site/build/market_history.py */\nwindow.ATLAS = window.ATLAS || {};\nwindow.ATLAS.marketHistory = '
                   + json.dumps(data, separators=(',', ':')) + ';\n', encoding='utf-8')
    print('wrote', OUT, OUT.stat().st_size // 1024, 'KB')


if __name__ == '__main__':
    main()
