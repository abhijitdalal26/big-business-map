"""Build site/data/companies.js (window.ATLAS.directory) from data_analysis/output/companies.js.

The source file (15,175 companies, ~5.9 MB) is copied in a compact form: repeated strings
(country, sector, list...) are dictionary-encoded, numbers rounded, descriptions cut to 220 chars.
Run: python site/build/directory.py
"""
import json, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'data_analysis', 'output', 'companies.js')
OUT = os.path.join(ROOT, 'site', 'data', 'companies.js')

s = open(SRC, encoding='utf-8').read()
d = json.loads(s[s.index('{'):s.rindex('}') + 1])
cols = d['columns']
ix = {c: i for i, c in enumerate(cols)}


# ---- 2026 overlay: refresh Forbes/Fortune figures and add India-unlisted + large private firms ----
import re
import pandas as pd
DATA = os.path.join(ROOT, 'data')
def _nk(n): return re.sub(r'[^a-z0-9]', '', str(n).lower())
_old = {}
for _r in d['rows']:
    _old.setdefault(_nk(_r[ix['company']]), _r)
def _f(v):
    try:
        f = float(v)
        return None if f != f else f
    except (TypeError, ValueError):
        return None
def _put(r, key, v):
    r[ix[key]] = v
def _upsert(name, vals, new_defaults):
    r = _old.get(_nk(name))
    if r is None:
        r = [None] * len(cols); _put(r, 'company', name)
        for k, v in new_defaults.items(): _put(r, k, v)
        d['rows'].append(r); _old[_nk(name)] = r
    for k, v in vals.items():
        if v is not None and v != '': _put(r, k, v)
    return r
_g = pd.read_csv(os.path.join(DATA, 'global2000_2026.csv'), encoding='utf-8-sig')
for _, x in _g.iterrows():
    _upsert(x.company, dict(revenue_usd=(_f(x.revenue_musd) or 0) * 1e6 if _f(x.revenue_musd) is not None else None,
            profit_usd=_f(x.profits_musd) * 1e6 if _f(x.profits_musd) is not None else None,
            assets_usd=_f(x.assets_musd) * 1e6 if _f(x.assets_musd) is not None else None,
            market_cap_usd=_f(x.market_value_musd) * 1e6 if _f(x.market_value_musd) is not None else None,
            employees=_f(x.employees), revenue_year='2025', revenue_basis='forbes', rank_in_source=_f(x['rank']),
            list_name='Forbes Global 2000', confidence='reported'),
            dict(country=x.country, sector=x.sector, industry_canon=x.industry_canon, ownership='public',
                 ceo=x.ceo if isinstance(x.ceo, str) else '', city=x.city if isinstance(x.city, str) else '',
                 website=x.website if isinstance(x.website, str) else '', description=(x.description if isinstance(x.description, str) else ''),
                 year_founded=_f(x.year_founded), n_sources=1))
_m = pd.read_csv(os.path.join(DATA, 'companies_master.csv'), encoding='utf-8-sig')
for _, x in _m[_m.source.str.startswith('Fortune Global 500')].iterrows():
    _upsert(x.company, dict(revenue_usd=_f(x.revenue_musd) * 1e6 if _f(x.revenue_musd) is not None else None,
            profit_usd=_f(x.profits_musd) * 1e6 if _f(x.profits_musd) is not None else None,
            assets_usd=_f(x.assets_musd) * 1e6 if _f(x.assets_musd) is not None else None,
            employees=_f(x.employees), revenue_year='2025', revenue_basis='fortune', list_name='Fortune Global 500', confidence='reported'),
            dict(country=x.country, sector=x.sector, industry_canon=x.industry_canon, ownership=str(x.ownership).lower().split()[0] if isinstance(x.ownership, str) else 'unknown', n_sources=1))
_OWN = {'private': 'private', 'state': 'state', 'co-op': 'mutual', 'subsidiary': 'private', 'family': 'private'}
for _fn, _ln, _ctry in (('india_unlisted.csv', 'India unlisted (Business Standard BS1000, Hurun)', 'India'), ('private_global.csv', 'Large private firms (global, Wikipedia/company reports)', None)):
    for _, x in pd.read_csv(os.path.join(DATA, 'extra', _fn), encoding='utf-8-sig').iterrows():
        _upsert(x.company, dict(revenue_usd=_f(x.revenue_musd) * 1e6 if _f(x.revenue_musd) is not None else None, revenue_year=str(x.revenue_year),
                revenue_basis='estimate', list_name=_ln, confidence='estimate' if x.confidence == 'low' else 'reported', website=x.url if isinstance(x.url, str) else ''),
                dict(country=_ctry or x.country, sector='Unclassified', industry_canon=x.sector, ownership=_OWN.get(str(x.ownership).lower(), 'private'),
                     city=x.hq_city if isinstance(x.hq_city, str) else '', n_sources=1))

_reg = {}
for _r in d['rows']:
    if _r[ix['region']]: _reg.setdefault(_r[ix['country']], _r[ix['region']])
for _r in d['rows']:
    if not _r[ix['region']]: _r[ix['region']] = _reg.get(_r[ix['country']], '')

DICT_COLS = ['country', 'region', 'sector', 'industry_canon', 'ownership', 'list_name', 'confidence', 'revenue_basis', 'revenue_year']
NUM_COLS = ['revenue_usd', 'profit_usd', 'assets_usd', 'market_cap_usd', 'valuation_usd', 'employees']
TXT_COLS = ['company', 'ticker', 'website', 'wikipedia', 'forbes_page', 'city', 'ceo', 'description']
dicts = {c: [] for c in DICT_COLS}
lookup = {c: {} for c in DICT_COLS}

def enc(c, v):
    v = v or ''
    if v not in lookup[c]:
        lookup[c][v] = len(dicts[c]); dicts[c].append(v)
    return lookup[c][v]

def num(v):
    if v is None: return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f: return None
    return int(round(f))

out_cols = TXT_COLS + DICT_COLS + NUM_COLS + ['n_sources', 'year_founded', 'g2k']
rows = []
for r in d['rows']:
    row = []
    for c in TXT_COLS:
        v = r[ix[c]] or ''
        if c == 'description' and len(v) > 220:
            v = v[:217].rsplit(' ', 1)[0] + '…'
        if c in ('website', 'wikipedia', 'forbes_page'):
            v = v.replace('https://en.wikipedia.org/wiki/', 'w:').replace('https://www.forbes.com/companies/', 'f:')
        row.append(v)
    row += [enc(c, r[ix[c]]) for c in DICT_COLS]
    row += [num(r[ix[c]]) for c in NUM_COLS]
    yf = num(r[ix['year_founded']])
    row += [num(r[ix['n_sources']]), yf, 1 if (r[ix['forbes_page']] or '').startswith('https://www.forbes.com/companies/') else 0]
    rows.append(row)

data = dict(columns=out_cols, dicts=dicts, rows=rows,
            note='Compact copy of data_analysis/output/companies.js. w: = https://en.wikipedia.org/wiki/, f: = https://www.forbes.com/companies/')
with open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('/* generated by site/build/directory.py from data_analysis/output/companies.js */\nwindow.ATLAS = window.ATLAS || {};\nwindow.ATLAS.directory = ')
    fh.write(json.dumps(data, ensure_ascii=False, separators=(',', ':')))
    fh.write(';\n')
print(len(rows), 'rows', os.path.getsize(OUT) // 1024, 'KB', 'g2k flagged', sum(r[-1] for r in rows))
for c in DICT_COLS: print(c, len(dicts[c]))
