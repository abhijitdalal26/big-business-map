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
import unicodedata
_LEGAL = {'inc', 'incorporated', 'corp', 'corporation', 'co', 'company', 'ltd', 'limited', 'plc', 'nv', 'ag', 'sa', 'se',
          'spa', 'ab', 'asa', 'oyj', 'as', 'bhd', 'berhad', 'tbk', 'llc', 'lp', 'kgaa', 'gmbh', 'holding', 'holdings', 'group', 'cos', 'companies'}
def _nkw(n):
    """Match key: 'NVIDIA CORP' = 'NVIDIA', 'The Home Depot' = 'Home Depot', 'JPMorgan Chase' = 'JPMorganChase',
    'Alibaba Group Holding Limited' = 'Alibaba Group'. Legal endings are removed repeatedly; spaces ignored."""
    s = unicodedata.normalize('NFKD', str(n)).encode('ascii', 'ignore').decode().lower().replace('&', ' and ')
    s = re.sub(r"['’`]", '', s)                      # McDonald's = McDONALDS
    w = re.sub(r'[^a-z0-9]+', ' ', s).split()
    j = []                                                # glue runs of single letters: U.S. -> us, N.V. -> nv, S.F. -> sf
    for x in w:
        if len(x) == 1 and j and j[-1][0] == '\0':
            j[-1] += x
        else:
            j.append('\0' + x if len(x) == 1 else x)
    w = [x.lstrip('\0') for x in j]
    w = ['corporation' if x == 'corp' else x for x in w]  # Aluminum Corp of China = Aluminum Corporation of China
    if w and w[0] in ('the', 'pt') and len(w) > 1:        # "The Home Depot", Indonesian "PT ..."
        w = w[1:]
    while len(w) > 1 and w[-1] in _LEGAL:
        w = w[:-1]
    return w
def _nk(n):
    return ''.join(_nkw(n))
_old = {}
for _r in d['rows']:
    _old.setdefault((_nk(_r[ix['company']]), _r[ix['country']] or ''), _r)
_MERGED = []
_FRESH = set()  # ids of rows written by the 2026 overlay
def _f(v):
    try:
        f = float(v)
        return None if f != f else f
    except (TypeError, ValueError):
        return None
def _put(r, key, v):
    r[ix[key]] = v
def _upsert(name, vals, new_defaults):
    # Same company = same match key AND same country, so look-alike names abroad never merge.
    ctry = new_defaults.get('country') or ''
    key = (_nk(name), ctry)
    r = _old.get(key)
    if r is None:
        r = [None] * len(cols); _put(r, 'company', name)
        for k, v in new_defaults.items(): _put(r, k, v)
        d['rows'].append(r); _old[key] = r
    elif r[ix['company']] != name:
        _MERGED.append((r[ix['company']], name))
        _put(r, 'company', name)  # show the list's clean name ("NVIDIA", not "NVIDIA CORP")
        _put(r, 'n_sources', (r[ix['n_sources']] or 1) + 1)
    _FRESH.add(id(r))
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

# ---- final merge: one row per company ----
# The analysis file itself holds some duplicates (e.g. "Mastercard" from Forbes 2025 and "Mastercard Incorporated"
# from the listed universe). Rows with the same match key and country are one company: keep the most trusted
# source's figures and fill gaps from the others. Rows whose revenues differ more than 5x are left alone and
# logged, because that usually means two different companies.
_RANK = {'Forbes Global 2000': 0, 'Fortune Global 500': 1, 'Listed universe': 3}
# Checked by hand: same company, but names differ beyond what the key handles
_ALIAS = {'Powergrid Corporation of India': 'Power Grid of India', 'Fastighets AB Balder': 'Fastighets Balder', 'NV Bekaert': 'Bekaert'}
for _r in d['rows']:
    if _r[ix['company']] in _ALIAS:
        _r[ix['company']] = _ALIAS[_r[ix['company']]]
# Same bank; the SEC row used a narrow revenue line, so the 5x revenue guard would keep them apart
_FORCE = {_nk('Huntington Bancshares'), _nk('Comerica')}
def _trust(r):
    # a row refreshed with 2026 figures always wins over a stale one
    return (0 if id(r) in _FRESH else 1, _RANK.get(r[ix['list_name']], 2 if str(r[ix['list_name']]).startswith('List of') else 4),
            -sum(v not in (None, '') for v in r))
_groups = {}
for _r in d['rows']:
    _groups.setdefault((_nk(_r[ix['company']]), _r[ix['country']] or ''), []).append(_r)
_drop, _SKIPPED, _N_FINAL = set(), [], 0
for (_k, _c), _rs in _groups.items():
    if len(_rs) < 2 or not _k or not _c:
        continue
    _rs.sort(key=_trust)
    _p = _rs[0]
    for _o in _rs[1:]:
        a, b = _f(_p[ix['revenue_usd']]), _f(_o[ix['revenue_usd']])
        if a and b and max(a, b) / min(a, b) > 5 and _k not in _FORCE:
            _SKIPPED.append((_p[ix['company']], _o[ix['company']], round(a / 1e9, 1), round(b / 1e9, 1))); continue
        for _ci in range(len(cols)):
            if _p[_ci] in (None, '') and _o[_ci] not in (None, ''):
                _p[_ci] = _o[_ci]
        _p[ix['n_sources']] = (_p[ix['n_sources']] or 1) + (_o[ix['n_sources']] or 1)
        _drop.add(id(_o)); _N_FINAL += 1
d['rows'] = [_r for _r in d['rows'] if id(_r) not in _drop]

# ---- second pass: name variants and a different recorded country, confirmed by revenue ----
# "AMAZON.COM, INC." = "Amazon", "Taiwan Semiconductor Manufacturing" = "Taiwan Semiconductor", Seagate filed under
# Ireland in one source and the US in another. A name match alone is not enough (Merck & Co. vs Merck KGaA,
# Toyota Motor vs Toyota Tsusho), so both rows must also report revenue, and the revenues must agree:
#   same country (or one blank): names equal or one starts with the other, revenue within 25%
#   different country:           names equal or one starts with the other, revenue within 10%
_ABBR = {  # abbreviations no rule can catch; each checked against Forbes 2026 names and revenue
    'TSMC': 'Taiwan Semiconductor', 'INTERNATIONAL BUSINESS MACHINES CORPORATION': 'IBM', 'GENERAL ELECTRIC COMPANY': 'GE Aerospace',
    'Saudi Aramco': 'Saudi Arabian Oil Company (Saudi Aramco)', 'Industrial & Commercial Bank of China': 'ICBC',
    'CATL': 'Contemporary Amperex Technology', 'Contemporary Amperex Technology (CATL)': 'Contemporary Amperex Technology',
    'Deere': 'John Deere', 'DEERE & CO': 'John Deere', 'Toronto-Dominion Bank': 'TD Bank Group', 'Bank of Montreal': 'BMO',
    'Banco Bilbao Vizcaya Argentaria': 'BBVA-Banco Bilbao Vizcaya Argentaria', 'CM Bank': 'China Merchants Bank',
    'Banco Santander': 'Santander', 'Foxconn (Hon Hai Precision Industry)': 'Hon Hai Precision', 'Hon Hai Precision Industry': 'Hon Hai Precision',
    'Bank of New York (BNY)': 'Bank of New York Mellon', 'Nippon Telegraph and Telephone': 'NTT', 'RBC': 'Royal Bank of Canada',
    'Compagnie Financière Richemont': 'Richemont', 'Nippon Telegraph & Tel': 'NTT', 'NTT (Nippon Telegraph & Telephone)': 'NTT',
    'Mitsui Bussan': 'Mitsui & Co.', 'UPS': 'United Parcel Service (UPS)', 'CIBC (Canadian Imperial Bank of Commerce)': 'Canadian Imperial Bank',
    'Canadian Imperial Bank of Commerce': 'Canadian Imperial Bank', 'BNY Mellon (Bank of New York Mellon)': 'Bank of New York Mellon',
    'OCBC Bank': 'Oversea-Chinese Banking', 'MercadoLibre, Inc.': 'MercadoLibre', 'National Australia Bank': 'NAB - National Australia Bank',
    'Dior - LVMH': 'Christian Dior'}
def _within(a, b, tol):
    return a and b and max(a, b) / min(a, b) <= 1 + tol
def _namefit(n1, n2, same_country):
    # Different country: names must match exactly. Same country: the shorter name may also be the first whole
    # words of the longer one ("Amazon" = "Amazon.com"), but never a word fragment ("Disco" vs "Discover").
    w1, w2 = _nkw(n1), _nkw(n2)
    if ''.join(w1) == ''.join(w2):
        return True
    if not same_country:
        return False
    a, b = (w1, w2) if len(w1) <= len(w2) else (w2, w1)
    return len(''.join(a)) >= 4 and b[:len(a)] == a
# Checked by hand: similar names, different companies (parent vs listed subsidiary, or unrelated)
_NEVER = {frozenset(map(_nk, x)) for x in [('Tokyu', 'Tokyu Fudosan'), ('Doosan', 'Doosan Enerbility'),
          ('Godrej', 'Godrej & Boyce Manufacturing Company'), ('Charoen Pokphand Group', 'Charoen Pokphand Foods'),
          ('Sompo', 'Sompo Japan Nipponkoa Insurance'), ('Genesis Energy LP', 'Genesis Energy'), ('Super Group', 'Super Retail Group')]}
# regional placeholders some sources use instead of a country
_VAGUE = {'Europe', 'World (private)', 'Africa', 'Southeast Asia', 'International', 'D.C.'}
_kept, _bucket, _FUZZY = [], {}, []
for _o in sorted(d['rows'], key=_trust):
    _ko = _nk(_ABBR.get(_o[ix['company']], _o[ix['company']])); _ro = _f(_o[ix['revenue_usd']]); _co = _o[ix['country']] or ''
    _hit = None
    if _ko and _ro:
        _wo = _nkw(_ABBR.get(_o[ix['company']], _o[ix['company']]))
        _cands = {id(x): x for x in _bucket.get(_ko[:5], []) + _bucket.get('w:' + (_wo[0] if _wo else ''), [])}.values()
        for _p in _cands:
            _kp = _nk(_ABBR.get(_p[ix['company']], _p[ix['company']])); _rp = _f(_p[ix['revenue_usd']]); _cp = _p[ix['country']] or ''
            _no, _np = _ABBR.get(_o[ix['company']], _o[ix['company']]), _ABBR.get(_p[ix['company']], _p[ix['company']])
            same = not _co or not _cp or _co == _cp or _co in _VAGUE or _cp in _VAGUE
            if not _namefit(_no, _np, same) or frozenset((_ko, _kp)) in _NEVER:
                continue
            if (_o[ix['company']] in _ABBR or _p[ix['company']] in _ABBR) and _ko == _kp:
                _hit = _p; break  # hand-checked alias: banks report "revenue" differently, so skip the revenue test
            _mo, _mp = _f(_o[ix['market_cap_usd']]), _f(_p[ix['market_cap_usd']])
            if not same and _mo and _mp and not _within(_mo, _mp, 0.5):
                continue
            # different country: also needs agreeing market values (checked above when both exist)
            if _within(_ro, _rp, 0.25) and (same or (_mo and _mp)):
                _hit = _p; break
    if _hit is None:
        _kept.append(_o); _bucket.setdefault(_ko[:5], []).append(_o)
        _w1 = _nkw(_ABBR.get(_o[ix['company']], _o[ix['company']]))
        if _w1:
            _bucket.setdefault('w:' + _w1[0], []).append(_o)
        continue
    _FUZZY.append((_hit[ix['company']], _hit[ix['country']], _o[ix['company']], _o[ix['country']], _o[ix['list_name']],
                   round((_f(_o[ix['market_cap_usd']]) or 0) / 1e9)))
    for _ci in range(len(cols)):
        if _hit[_ci] in (None, '') and _o[_ci] not in (None, ''):
            _hit[_ci] = _o[_ci]
    _hit[ix['n_sources']] = (_hit[ix['n_sources']] or 1) + (_o[ix['n_sources']] or 1)
_order = {id(r): i for i, r in enumerate(d['rows'])}
d['rows'] = sorted(_kept, key=lambda r: _order[id(r)])
print('second pass (name variant / other country, revenue agrees): merged', len(_FUZZY), 'rows')
with open(os.path.join(ROOT, 'site', 'build', 'directory_merges.csv'), 'w', encoding='utf-8', newline='') as _fh:
    import csv as _csv
    _w = _csv.writer(_fh); _w.writerow(['kept', 'kept_country', 'merged_in', 'merged_country', 'merged_list', 'merged_mcap_busd'])
    _w.writerows(sorted(_FUZZY, key=lambda x: -x[5]))
# Forbes rows the 2026 list did not refresh are 2025-only: say so, instead of passing them off as current
_n25 = 0
for _r in d['rows']:
    if _r[ix['list_name']] == 'Forbes Global 2000' and id(_r) not in _FRESH:
        _r[ix['list_name']] = 'Forbes Global 2000 (2025 list only)'; _n25 += 1
print('Forbes rows not on the 2026 list, relabelled:', _n25)
print('final merge: removed', _N_FINAL, 'duplicate rows; left apart (revenue differs >5x):', _SKIPPED)

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
print('merged into existing rows:', len(_MERGED), _MERGED[:12])
print(len(rows), 'rows', os.path.getsize(OUT) // 1024, 'KB', 'g2k flagged', sum(r[-1] for r in rows))
for c in DICT_COLS: print(c, len(dicts[c]))
