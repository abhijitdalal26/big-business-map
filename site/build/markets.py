"""Build site/data/markets.js for markets.html ("The world's stock markets").

Inputs (all precomputed elsewhere in the project, reused here):
  stock_market/data/exchanges.csv, exchange_companies.csv
  listed_universe/data/listed_universe.csv, cmc_list.csv, company_profiles.csv
  data/global2000_2026.csv, data/country_gdp_2024.csv, data/world_macro.csv
  data_analysis/output/data/capital__financial_depth.csv
  World Bank API (CM.MKT.LCAP.GD.ZS, CM.MKT.LCAP.CD, CM.MKT.LDOM.NO) cached in site/build/cache/

Run:  python site/build/markets.py
"""
import json, re, os, urllib.request
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / 'site'
CACHE = Path(__file__).resolve().parent / 'cache'
CACHE.mkdir(exist_ok=True)

def rd(p):
    return pd.read_csv(ROOT / p, encoding='utf-8-sig')

FIX = {'Nestl�': 'Nestlé', 'Oslo B�rs': 'Oslo Børs', 'B3 (Brasil Bolsa Balc�o)': 'B3 (Brasil Bolsa Balcão)'}
def fix(s):
    s = str(s)
    for a, b in FIX.items():
        s = s.replace(a, b)
    return s.replace('�', '?')

# ---------------------------------------------------------------- World Bank
WB = ['CM.MKT.LCAP.GD.ZS', 'CM.MKT.LCAP.CD', 'CM.MKT.LDOM.NO']
def wb(ind):
    f = CACHE / f'wb_{ind}.json'
    if not f.exists():
        url = f'https://api.worldbank.org/v2/country/all/indicator/{ind}?format=json&date=1990:2024&per_page=20000'
        f.write_bytes(urllib.request.urlopen(url, timeout=120).read())
    rows = json.loads(f.read_text(encoding='utf-8'))[1]
    return pd.DataFrame([{'iso3': r['countryiso3code'], 'name': r['country']['value'], 'year': int(r['date']), 'v': r['value']}
                         for r in rows if r['value'] is not None and r['countryiso3code']])
wbd = {i: wb(i) for i in WB}

# ---------------------------------------------------------------- regions (hand map for every exchange country)
REGION = {
 'United States': 'North America', 'Canada': 'North America', 'Mexico': 'Latin America', 'Brazil': 'Latin America',
 'Chile': 'Latin America', 'Argentina': 'Latin America',
 'Japan': 'East Asia', 'China': 'East Asia', 'Hong Kong': 'East Asia', 'Taiwan': 'East Asia', 'South Korea': 'East Asia',
 'Singapore': 'Southeast Asia', 'Thailand': 'Southeast Asia', 'Indonesia': 'Southeast Asia', 'Malaysia': 'Southeast Asia',
 'Vietnam': 'Southeast Asia', 'Philippines': 'Southeast Asia',
 'India': 'South Asia', 'Australia': 'Oceania', 'New Zealand': 'Oceania',
 'Saudi Arabia': 'Middle East & Africa', 'United Arab Emirates': 'Middle East & Africa', 'Qatar': 'Middle East & Africa',
 'Kuwait': 'Middle East & Africa', 'Oman': 'Middle East & Africa', 'Bahrain': 'Middle East & Africa', 'Israel': 'Middle East & Africa',
 'South Africa': 'Middle East & Africa', 'Turkey': 'Middle East & Africa',
}
REGIONS = ['North America', 'Europe', 'East Asia', 'South Asia', 'Southeast Asia', 'Middle East & Africa', 'Latin America', 'Oceania']
def region(c):
    return REGION.get(c, 'Europe')

# ---------------------------------------------------------------- sectors
# 7 named groups + Other (colour rule: <=8). Forbes 13 sectors fold into them.
SEC_FOLD = {
 'Technology': 'Technology', 'Financials': 'Financials', 'Healthcare': 'Healthcare',
 'Consumer & Retail': 'Consumer', 'Food & Agriculture': 'Consumer',
 'Energy & Utilities': 'Energy & Materials', 'Materials & Chemicals': 'Energy & Materials',
 'Industrials & Defense': 'Industrials', 'Transport & Logistics': 'Industrials', 'Construction & Real Estate': 'Industrials',
 'Business Services': 'Industrials', 'Conglomerates': 'Industrials', 'Telecom & Media': 'Telecom & Media',
}
SECTORS = ['Technology', 'Financials', 'Healthcare', 'Consumer', 'Energy & Materials', 'Industrials', 'Telecom & Media', 'Other / unclassified']

def norm(s):
    s = str(s).lower()
    s = re.sub(r'\(.*?\)', ' ', s)
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    s = re.sub(r'\b(inc|corp|corporation|co|ltd|limited|plc|group|holdings?|the|sa|ag|nv|se|company|asa|ab|spa|bhd|tbk|class [a-z]|and)\b', ' ', s)
    return ' '.join(s.split())

# manual sector for big names the Forbes name-match misses (keeps top-50 chart fully coloured)
MANUAL = {
 'Alphabet (Google)': 'Technology', 'TSMC': 'Technology', 'SpaceX': 'Industrials', 'Meta Platforms (Facebook)': 'Technology',
 'Saudi Aramco': 'Energy & Materials', 'Samsung': 'Technology', 'JPMorgan Chase': 'Financials', 'AMD': 'Technology',
 'Exxon Mobil': 'Energy & Materials', 'Palantir': 'Technology', 'Costco': 'Consumer', 'CXMT': 'Technology', 'Cisco': 'Technology',
 'General Electric': 'Industrials', 'Dell': 'Technology', 'Royal Bank Of Canada': 'Financials', 'Tencent': 'Technology',
 'Kweichow Moutai': 'Consumer', 'Wells Fargo': 'Financials', 'Goldman Sachs': 'Financials', 'Toyota': 'Consumer',
 'Mitsubishi UFJ Financial': 'Financials', 'Mitsubishi UFJ': 'Financials', 'LVMH': 'Consumer', 'Hermès': 'Consumer',
 'Novo Nordisk': 'Healthcare', 'AstraZeneca': 'Healthcare', 'Reliance Industries': 'Energy & Materials', 'Siemens': 'Industrials',
 'Salesforce': 'Technology', 'IBM': 'Technology', 'T-Mobile US': 'Telecom & Media', 'Abbott Laboratories': 'Healthcare',
 'Linde': 'Energy & Materials', 'Arm Holdings': 'Technology', 'McDonald': 'Consumer', 'Uber': 'Technology', 'Pepsico': 'Consumer',
 'Thermo Fisher Scientific': 'Healthcare', 'American Express': 'Financials', 'Walt Disney': 'Telecom & Media', 'Verizon': 'Telecom & Media',
 'AT&T': 'Telecom & Media', 'Texas Instruments': 'Technology', 'Qualcomm': 'Technology', 'Booking Holdings': 'Consumer',
 'Intuitive Surgical': 'Healthcare', 'ServiceNow': 'Technology', 'Adobe': 'Technology', 'KLA': 'Technology', 'Xiaomi': 'Technology',
 'BYD': 'Consumer', 'Industrial Bank of Korea': 'Financials', 'Petrochina': 'Energy & Materials', 'PetroChina': 'Energy & Materials',
 'China Mobile': 'Telecom & Media', 'Bharti Airtel': 'Telecom & Media', 'HDFC Bank': 'Financials', 'HDFC BANK LIMITED': 'Financials',
 'ICICI Bank': 'Financials', 'State Bank of India': 'Financials', 'Tata Consultancy Services': 'Technology', 'Infosys': 'Technology',
 'Bajaj Finance': 'Financials', 'Larsen & Toubro': 'Industrials', 'Hindustan Unilever': 'Consumer', 'Sun Pharmaceutical': 'Healthcare',
 'Kotak Mahindra Bank': 'Financials', 'Nestlé': 'Consumer', 'Commonwealth Bank': 'Financials', 'International Holding Company': 'Industrials',
 'Broadcom': 'Technology', 'Micron Technology': 'Technology', 'Lam Research': 'Technology', 'Applied Materials': 'Technology',
 'UnitedHealth': 'Healthcare', 'Tesla': 'Consumer', 'SK Hynix': 'Technology', 'Mitsubishi': 'Industrials',
 'Tokyo Electron': 'Technology', 'CM Bank': 'Financials', 'Unimicron': 'Technology', 'ASML': 'Technology',
}

KW = [  # (sector, regex) applied to a company's description, first hit wins
 ('Financials', r'\b(bank|banking|insurance|insurer|reinsur|asset management|investment (firm|company|trust|management)|brokerage|financial services|stock exchange|lender|mortgage|credit card|payments?|reit|private equity|fintech)\b'),
 ('Healthcare', r'\b(pharmaceutical|biotech|biotechnology|medical|health ?care|hospital|drug|therapeut|diagnostic|vaccine|clinical)\b'),
 ('Telecom & Media', r'\b(telecommunication|telecom|mobile network|wireless carrier|broadcast|media company|television|newspaper|publishing|entertainment|cable|satellite operator|video game)\b'),
 ('Technology', r'\b(software|semiconductor|chip|internet|cloud|e-commerce|electronics|computer|information technology|it services|data center|cybersecurity|online)\b'),
 ('Energy & Materials', r'\b(oil|gas|petroleum|energy|electric utility|utility|utilities|power generation|electricity|mining|miner|metals?|steel|copper|gold|chemicals?|fertili[sz]er|cement|aluminium|aluminum|coal|lithium|paper|renewable)\b'),
 ('Consumer', r'\b(retail|retailer|supermarket|food|beverage|brewer|beer|restaurant|apparel|fashion|luxury|cosmetic|tobacco|automaker|automobile|car manufacturer|vehicles?|hotel|consumer|grocery|household|airline)\b'),
 ('Industrials', r'\b(industrial|engineering|construction|aerospace|defen[cs]e|machinery|conglomerate|logistics|shipping|railway|airport|real estate|property|infrastructure|manufactur|equipment|transport)\b'),
]
KW = [(s, re.compile(r, re.I)) for s, r in KW]
def kw_sector(desc):
    if not isinstance(desc, str):
        return None
    d = desc[:600]
    best = None
    for s, rx in KW:
        m = rx.search(d)
        if m and (best is None or m.start() < best[1]):
            best = (s, m.start())
    return best[0] if best else None

forbes = rd('data/global2000_2026.csv')
forbes_sec = {}
for c, s in zip(forbes.company, forbes.sector):
    forbes_sec.setdefault(norm(c), SEC_FOLD.get(s))
cmc = rd('listed_universe/data/cmc_list.csv')
prof = rd('listed_universe/data/company_profiles.csv')
desc_by_slug = dict(zip(prof.ticker_or_slug, prof.description))
slug_by_ticker = dict(zip(cmc.ticker, cmc.slug))

def sector_of(name, ticker):
    if name in MANUAL:
        return MANUAL[name], 'manual'
    s = forbes_sec.get(norm(name))
    if s:
        return s, 'forbes'
    s = kw_sector(desc_by_slug.get(slug_by_ticker.get(ticker)))
    if s:
        return s, 'keyword'
    return 'Other / unclassified', 'none'

# ---------------------------------------------------------------- exchanges & companies
ex = rd('stock_market/data/exchanges.csv')
ec = rd('stock_market/data/exchange_companies.csv')
for d in (ex, ec):
    d['exchange'] = d['exchange'].map(fix)
ec['company'] = ec['company'].map(fix)
ex['top_company'] = ex['top_company'].map(fix)
sec = ec.apply(lambda r: sector_of(r.company, r.ticker), axis=1)
ec['sector'] = [s for s, _ in sec]
ec['sector_basis'] = [b for _, b in sec]
sector_cov = ec.groupby('sector_basis').market_cap_usd.sum() / ec.market_cap_usd.sum()
print('sector basis by mcap:', sector_cov.round(3).to_dict())

ec = ec.sort_values('market_cap_usd', ascending=False).reset_index(drop=True)
ec['world_rank'] = np.arange(1, len(ec) + 1)

def r3(x):
    return None if pd.isna(x) else float(f'{x:.4g}')

exchanges = []
for _, r in ex.sort_values('total_market_cap_usd', ascending=False).iterrows():
    sub = ec[ec.exchange == r.exchange]
    mix = sub.groupby('sector').market_cap_usd.sum()
    exchanges.append({
        'name': r.exchange, 'country': r.exchange_country, 'city': r.city, 'region': region(r.exchange_country),
        'n': int(r.companies), 'mcap': r3(r.total_market_cap_usd), 'top10': r3(r.top10_market_cap_usd),
        'top10_share': r3(r.top10_market_cap_usd / r.total_market_cap_usd),
        'avg': r3(r.total_market_cap_usd / r.companies), 'median': r3(sub.market_cap_usd.median()),
        'top': r.top_company, 'top_mcap': r3(r.top_company_mcap),
        'n1b': int((sub.market_cap_usd >= 1e9).sum()), 'n100b': int((sub.market_cap_usd >= 1e11).sum()),
        'mix': {s: r3(mix.get(s, 0)) for s in SECTORS if mix.get(s, 0) > 0},
        'cos': [[c.company, c.ticker, r3(c.market_cap_usd), r3(c.revenue_usd), SECTORS.index(c.sector), int(c.world_rank)]
                for c in sub.head(25).itertuples()],
    })

# treemap: country -> exchange -> top 12 companies + "rest of exchange"
tree = {}
for e in exchanges:
    sub = ec[ec.exchange == e['name']]
    kids = [{'name': c.company, 'value': r3(c.market_cap_usd), 'sector': c.sector} for c in sub.head(12).itertuples()]
    rest = sub.iloc[12:]
    if len(rest):
        kids.append({'name': f'{len(rest)} other companies', 'value': r3(rest.market_cap_usd.sum()), 'rest': len(rest)})
    tree.setdefault(e['country'], []).append({'name': e['name'], 'value': e['mcap'], 'n': e['n'], 'children': kids})
treemap = sorted([{'name': c, 'value': r3(sum(x['value'] for x in v)), 'n': sum(x['n'] for x in v), 'region': region(c), 'children': v}
                  for c, v in tree.items()], key=lambda x: -x['value'])

# top 100 companies worldwide
top = [{'name': c.company, 'ticker': c.ticker, 'ex': c.exchange, 'country': c.exchange_country, 'mcap': r3(c.market_cap_usd),
        'rev': r3(c.revenue_usd), 'sector': c.sector, 'rank': int(c.world_rank)} for c in ec.head(100).itertuples()]
trillion = [t for t in top if t['mcap'] >= 1e12]

# ---------------------------------------------------------------- distribution (listed universe, market-cap rows)
lu = rd('listed_universe/data/listed_universe.csv')
lu = lu[lu.market_cap_usd.notna() & (lu.market_cap_usd > 0)].copy()
lu['company'] = lu['company'].map(fix)
caps = np.sort(lu.market_cap_usd.values)[::-1]
tot = caps.sum()
cum = np.cumsum(caps) / tot
N = len(caps)
curve = []
for pct in sorted(set(list(np.round(np.linspace(0, 100, 201), 2)) + [0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 1, 2, 3, 5, 10, 20, 50])):
    k = max(1, int(round(N * pct / 100)))
    if pct == 0:
        continue
    curve.append([float(pct), round(float(cum[k - 1]) * 100, 2), k])
def share_top(k):
    return round(float(cum[k - 1]) * 100, 1)
dist_kpis = {'n': int(N), 'total': r3(tot), 'min': r3(caps.min()), 'median': r3(np.median(caps)),
             'top10': share_top(10), 'top100': share_top(100), 'top1pct': share_top(int(N * 0.01)), 'top10pct': share_top(int(N * 0.10)),
             'bottom50pct': round(100 - share_top(N // 2), 1)}
TH = [('$1T+', 1e12), ('$100B–1T', 1e11), ('$10B–100B', 1e10), ('$1B–10B', 1e9), ('Under $1B', 0)]
def band(v):
    for lbl, t in TH:
        if v >= t:
            return lbl
lu['band'] = lu.market_cap_usd.map(band)
lu['country'] = lu['country'].fillna('Unknown')
topc = lu.groupby('country').market_cap_usd.sum().sort_values(ascending=False).head(12).index.tolist()
if 'India' not in topc:
    topc.append('India')
bands = {}
for c in topc + ['Rest of world', 'World']:
    s = lu if c == 'World' else lu[~lu.country.isin(topc)] if c == 'Rest of world' else lu[lu.country == c]
    bands[c] = {'counts': {b: int((s.band == b).sum()) for b, _ in TH}, 'value': {b: r3(s[s.band == b].market_cap_usd.sum()) for b, _ in TH},
                'over': {k: int((s.market_cap_usd >= t).sum()) for k, t in [('1B', 1e9), ('10B', 1e10), ('100B', 1e11), ('1T', 1e12)]}}
# log histogram
edges = 10 ** np.arange(7.5, 12.9, 0.25)
hist, _ = np.histogram(lu.market_cap_usd.values, bins=edges)
histo = [[r3(edges[i]), r3(edges[i + 1]), int(hist[i])] for i in range(len(hist))]

# ---------------------------------------------------------------- valuation
lu_rev = lu[lu.revenue_usd.notna() & (lu.revenue_usd > 0)].copy()
lu_rev['ps'] = lu_rev.market_cap_usd / lu_rev.revenue_usd
val_country = []
for c, g in lu_rev.groupby('country'):
    if len(g) >= 25:
        val_country.append({'country': c, 'n': int(len(g)), 'median_ps': r3(g.ps.median()), 'agg_ps': r3(g.market_cap_usd.sum() / g.revenue_usd.sum()),
                            'p25': r3(g.ps.quantile(.25)), 'p75': r3(g.ps.quantile(.75))})
val_country.sort(key=lambda x: -x['median_ps'])
f2 = forbes[forbes.market_value_musd.notna() & (forbes.market_value_musd > 0)].copy()
f2['ps'] = f2.market_value_musd / f2.revenue_musd
f2['pe'] = np.where(f2.profits_musd > 0, f2.market_value_musd / f2.profits_musd, np.nan)
def val_group(key, minn):
    out = []
    for k, g in f2.groupby(key):
        if len(g) < minn:
            continue
        gp = g[g.profits_musd > 0]
        out.append({'k': k, 'n': int(len(g)), 'median_ps': r3(g.ps.median()), 'agg_ps': r3(g.market_value_musd.sum() / g.revenue_musd.sum()),
                    'median_pe': r3(gp.pe.median()), 'agg_pe': r3(gp.market_value_musd.sum() / gp.profits_musd.sum()),
                    'lossmakers': int((g.profits_musd <= 0).sum())})
    return sorted(out, key=lambda x: -x['median_ps'])
val_sector = val_group('sector', 10)
val_fcountry = val_group('country', 20)

# ---------------------------------------------------------------- financial depth
gdp = rd('data/country_gdp_2024.csv')
fd = rd('data_analysis/output/data/capital__financial_depth.csv')
wb_gd = wbd['CM.MKT.LCAP.GD.ZS']; wb_cd = wbd['CM.MKT.LCAP.CD']; wb_no = wbd['CM.MKT.LDOM.NO']
def latest(df, iso):
    s = df[df.iso3 == iso].sort_values('year')
    return (None, None) if s.empty else (float(s.v.iloc[-1]), int(s.year.iloc[-1]))
gdp_iso = dict(zip(gdp.iso3, gdp.gdp_usd)); name_iso = dict(zip(gdp.iso3, gdp.country))
depth = []
for r in fd.itertuples():
    wg, wy = latest(wb_gd[wb_gd.year >= 2019], r.iso3)
    wn, _ = latest(wb_no[wb_no.year >= 2019], r.iso3)
    wc, _ = latest(wb_cd[wb_cd.year >= 2019], r.iso3)
    depth.append({'country': r.country, 'iso3': r.iso3, 'gdp': r3(r.gdp), 'mcap': r3(r.market_cap), 'n': int(r.companies),
                  'ratio': r3(r.mcap_to_gdp * 100), 'wb_ratio': r3(wg), 'wb_year': wy, 'wb_mcap': r3(wc), 'wb_n': None if wn is None else int(wn),
                  'region': region(r.country)})
# World Bank-only countries with GDP >= $100B not in our coverage
have = {d['iso3'] for d in depth}
for iso, g in gdp_iso.items():
    if iso in have or g < 1e11:
        continue
    wg, wy = latest(wb_gd[wb_gd.year >= 2019], iso)
    if wg is None:
        continue
    wn, _ = latest(wb_no[wb_no.year >= 2019], iso); wc, _ = latest(wb_cd[wb_cd.year >= 2019], iso)
    depth.append({'country': name_iso[iso], 'iso3': iso, 'gdp': r3(g), 'mcap': None, 'n': 0, 'ratio': None, 'wb_ratio': r3(wg), 'wb_year': wy,
                  'wb_mcap': r3(wc), 'wb_n': None if wn is None else int(wn), 'region': 'n/a'})

# ---------------------------------------------------------------- time series
TS = {'WLD': 'World', 'USA': 'United States', 'CHN': 'China', 'IND': 'India', 'JPN': 'Japan', 'GBR': 'United Kingdom',
      'HKG': 'Hong Kong', 'KOR': 'South Korea', 'DEU': 'Germany', 'CAN': 'Canada', 'BRA': 'Brazil', 'SAU': 'Saudi Arabia'}
ts = {}
for iso, nm in TS.items():
    ts[nm] = {k: {int(y): r3(v) for y, v in zip(df[df.iso3 == iso].year, df[df.iso3 == iso].v)}
              for k, df in [('n', wb_no), ('mcap', wb_cd), ('gdp_pct', wb_gd)]}
w_no = ts['World']['n']; w_cd = ts['World']['mcap']

# ---------------------------------------------------------------- India pack
ind_ex = [e for e in exchanges if e['country'] == 'India']
ex_rank_mcap = [e['name'] for e in exchanges]
ex_rank_n = [e['name'] for e in sorted(exchanges, key=lambda e: -e['n'])]
nse = next(e for e in exchanges if e['name'].startswith('National Stock Exchange'))
cty_mcap = lu.groupby('country').market_cap_usd.sum().sort_values(ascending=False)
wld_gdp = float(rd('data/world_macro.csv').query("indicator=='NY.GDP.MKTP.CD'").sort_values('year').value.iloc[-1])
ind_wb_mcap = ts['India']['mcap'].get(2024); wld_wb_mcap = w_cd.get(2024)
india = {
    'nse_n': nse['n'], 'nse_mcap': nse['mcap'], 'nse_rank_mcap': ex_rank_mcap.index(nse['name']) + 1, 'nse_rank_n': ex_rank_n.index(nse['name']) + 1,
    'country_rank': int(list(cty_mcap.index).index('India') + 1), 'country_mcap': r3(cty_mcap['India']),
    'share_cov': r3(cty_mcap['India'] / cty_mcap.sum() * 100),
    'wb_mcap_2024': ind_wb_mcap, 'wb_share_2024': r3(ind_wb_mcap / wld_wb_mcap * 100), 'wb_n_2024': ts['India']['n'].get(2024),
    'wb_gdp_pct_2024': ts['India']['gdp_pct'].get(2024), 'gdp': r3(gdp_iso['IND']), 'gdp_share': r3(gdp_iso['IND'] / wld_gdp * 100),
    'top': [{'name': c.company, 'mcap': r3(c.market_cap_usd), 'rev': r3(c.revenue_usd), 'rank': int(c.world_rank), 'sector': c.sector}
            for c in ec[ec.exchange_country == 'India'].head(15).itertuples()],
    'over': bands['India']['over'],
    'bse_n': next((e['n'] for e in ind_ex if e['name'].startswith('Bombay')), 0),
}

out = {
    'meta': {'snapshot': 'Oct 2026 (CompaniesMarketCap)', 'wb_year': 2024, 'sectors': SECTORS, 'regions': REGIONS,
             'sector_basis': {k: round(float(v), 3) for k, v in sector_cov.items()},
             'n_assigned': int(len(ec)), 'assigned_total': r3(ec.market_cap_usd.sum()),
             'n_universe': int(rd('listed_universe/data/listed_universe.csv').shape[0]),
             'wb_listed_2024': w_no.get(2024), 'wb_mcap_2024': w_cd.get(2024), 'wb_gdp_pct_2024': ts['World']['gdp_pct'].get(2024),
             'world_gdp': r3(wld_gdp)},
    'exchanges': exchanges, 'treemap': treemap, 'top': top, 'trillion': trillion,
    'dist': {'curve': curve, 'kpis': dist_kpis, 'bands': bands, 'band_labels': [b for b, _ in TH], 'countries': topc + ['Rest of world'], 'hist': histo},
    'val': {'sector': val_sector, 'fcountry': val_fcountry, 'country': val_country},
    'depth': depth, 'ts': ts, 'india': india,
}
js = 'window.ATLAS = window.ATLAS || {};\nwindow.ATLAS.markets = ' + json.dumps(out, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + ';\n'
(SITE / 'data').mkdir(exist_ok=True)
(SITE / 'data' / 'markets.js').write_text(js, encoding='utf-8')
print('wrote markets.js', round(len(js.encode()) / 1e6, 2), 'MB')
print(json.dumps({k: out['meta'][k] for k in out['meta'] if k not in ('sectors', 'regions')}, indent=1))
print('india', json.dumps({k: v for k, v in india.items() if k != 'top'}))
print('dist', dist_kpis)
print('trillion', [(t['name'], round(t['mcap'] / 1e12, 2)) for t in trillion])
