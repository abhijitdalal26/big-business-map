"""Build site/data/geography.js  (window.ATLAS.geography).

Reuses data_analysis/output/data/*.csv (precomputed country/region tables) and adds
unicorns + listed market cap by country, top firms per country and the India deep-dive.
Run: python site/build/geography.py
"""
import json, os, sys
import pandas as pd
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'data_analysis'))
import clean  # noqa: E402  (country vocabulary: name -> ISO3)

A = os.path.join(ROOT, 'data_analysis', 'output', 'data')
D = os.path.join(ROOT, 'data')
OUT = os.path.join(ROOT, 'site', 'data', 'geography.js')

def rd(p):
    return pd.read_csv(p, encoding='utf-8-sig')

meta = rd(os.path.join(D, 'country_meta.csv'))
meta['region'] = meta['region'].str.strip()
idx = clean.build_country_index(meta)
def iso(name):
    return clean.country_iso3(name, idx)

PRETTY = {
    'Korea, Rep.': 'South Korea', 'Hong Kong SAR, China': 'Hong Kong', 'Russian Federation': 'Russia',
    'Egypt, Arab Rep.': 'Egypt', 'Iran, Islamic Rep.': 'Iran', 'Turkiye': 'Turkey', 'Bahamas, The': 'Bahamas',
    'Macao SAR, China': 'Macau', 'Viet Nam': 'Vietnam', 'Slovak Republic': 'Slovakia', 'Venezuela, RB': 'Venezuela',
    'Czechia': 'Czech Republic', 'Gambia, The': 'Gambia', 'Yemen, Rep.': 'Yemen', 'Congo, Dem. Rep.': 'DR Congo',
    'Congo, Rep.': 'Congo', 'Lao PDR': 'Laos', 'Kyrgyz Republic': 'Kyrgyzstan', "Korea, Dem. People's Rep.": 'North Korea',
    'Micronesia, Fed. Sts.': 'Micronesia', 'St. Lucia': 'Saint Lucia', 'Brunei Darussalam': 'Brunei',
}
def pretty(n):
    return PRETTY.get(n, n)

gdp = rd(os.path.join(D, 'country_gdp_2024.csv'))[['iso3', 'gdp_usd']].dropna()
world_gdp = float(rd(os.path.join(D, 'world_macro.csv')).query("indicator=='NY.GDP.MKTP.CD' and year==2024")['value'].iloc[0])

# ---------- per-country frame ----------
names = {r.iso3: pretty(r['name']) for _, r in meta.iterrows()}
names['TWN'] = 'Taiwan'
region_of = {}
for _, r in meta.iterrows():
    region_of[r.iso3] = clean.WB_REGION_TO_FORBES.get(r['region'], 'Other')
region_of['TWN'] = 'Asia-Pacific'

C = {}
def row(i):
    if i not in C:
        C[i] = {'iso': i, 'name': names.get(i, i), 'region': region_of.get(i, 'Other')}
    return C[i]

for _, r in gdp.iterrows():
    row(r.iso3)['gdp'] = float(r.gdp_usd)

f = rd(os.path.join(A, 'geography__country_forbes.csv'))
for _, r in f.iterrows():
    c = row(r.country_iso3)
    c.update(g_n=int(r.companies), g_rev=float(r.revenue_usd), g_prof=float(r.profit_usd),
             g_mv=float(r.market_cap_usd), g_emp=float(r.employees), region=r.region)
    if pd.notna(r.population): c['pop'] = float(r.population)

m = rd(os.path.join(A, 'geography__country_mixed.csv'))
for _, r in m.iterrows():
    c = row(r.country_iso3)
    c.update(x_n=int(r.companies), x_rev=float(r.revenue_usd), x_mv=float(r.market_cap_usd), region=r.region)
    if pd.notna(r.population): c['pop'] = float(r.population)

u = rd(os.path.join(A, 'private_capital__unicorns_by_country.csv'))
unmatched_uni = []
for _, r in u.iterrows():
    i = iso(r.country)
    if not i:
        unmatched_uni.append(r.country); continue
    c = row(i); c['u_n'] = c.get('u_n', 0) + int(r.companies); c['u_val'] = c.get('u_val', 0) + float(r.valuation_usd)

fd = rd(os.path.join(A, 'capital__financial_depth.csv'))
for _, r in fd.iterrows():
    c = row(r.iso3); c['l_mv'] = float(r.market_cap); c['l_n'] = int(r.companies)

# top Forbes firms per country (for tooltips)
g2k = rd(os.path.join(D, 'global2000_2026.csv'))
g2k['iso'] = g2k.country.map(iso)
assert g2k.iso.notna().all(), g2k[g2k.iso.isna()].country.unique()
for i, grp in g2k.sort_values('revenue_musd', ascending=False).groupby('iso'):
    row(i)['top'] = ', '.join(grp.company.head(3))

countries = []
for c in C.values():
    has = any(k in c for k in ('g_n', 'x_n', 'u_n', 'l_mv'))
    if not has and c.get('gdp', 0) < 50e9:
        continue  # keep big economies (e.g. Russia) even with no companies
    for k, v in list(c.items()):
        if isinstance(v, float):
            c[k] = round(v, 0) if abs(v) > 1000 else round(v, 4)
    countries.append(c)
countries.sort(key=lambda c: -c.get('gdp', 0))

# ---------- regions ----------
reg_gdp = {}
for c in C.values():
    if 'gdp' in c: reg_gdp[c['region']] = reg_gdp.get(c['region'], 0) + c['gdp']
regions = []
rf = rd(os.path.join(A, 'geography__regions_forbes.csv')).set_index('region')
rm = rd(os.path.join(A, 'geography__regions_mixed.csv')).set_index('region')
reg_u = {}
for c in C.values():
    if 'u_val' in c:
        reg_u.setdefault(c['region'], [0, 0]); reg_u[c['region']][0] += c['u_n']; reg_u[c['region']][1] += c['u_val']
for reg in rf.index:
    regions.append(dict(region=reg, gdp=reg_gdp.get(reg, 0), gdp_share=reg_gdp.get(reg, 0) / world_gdp,
                        g_n=int(rf.loc[reg, 'companies']), g_rev=float(rf.loc[reg, 'revenue_usd']),
                        g_prof=float(rf.loc[reg, 'profit_usd']), g_mv=float(rf.loc[reg, 'market_cap_usd']),
                        g_rev_share=float(rf.loc[reg, 'revenue_share']), g_margin=float(rf.loc[reg, 'profit_margin']),
                        x_n=int(rm.loc[reg, 'companies']) if reg in rm.index else None,
                        x_rev_share=float(rm.loc[reg, 'revenue_share']) if reg in rm.index else None,
                        u_n=reg_u.get(reg, [0, 0])[0], u_val=reg_u.get(reg, [0, 0])[1]))

# ---------- head to head ----------
def agg(isos, label):
    out = dict(label=label)
    for k in ('gdp', 'g_n', 'g_rev', 'g_prof', 'g_mv', 'g_emp', 'u_n', 'u_val', 'l_mv', 'l_n', 'pop'):
        out[k] = sum(C[i].get(k, 0) or 0 for i in isos if i in C)
    return out
eu27 = ['AUT','BEL','BGR','HRV','CYP','CZE','DNK','EST','FIN','FRA','DEU','GRC','HUN','IRL','ITA','LVA','LTU','LUX','MLT','NLD','POL','PRT','ROU','SVK','SVN','ESP','SWE']
europe_all = [i for i, c in C.items() if c['region'] == 'Europe']
h2h = [agg(['USA'], 'United States'), agg(['CHN'], 'China (mainland)'), agg(['CHN', 'HKG', 'TWN', 'MAC'], 'Greater China (+HK, Taiwan)'),
       agg(eu27, 'EU-27'), agg(europe_all, 'Europe (all, incl. UK, Switz.)'), agg(['JPN'], 'Japan'), agg(['IND'], 'India')]
world = dict(gdp=world_gdp, g_n=2000, g_rev=float(g2k.revenue_musd.sum() * 1e6), g_prof=float(g2k.profits_musd.sum() * 1e6),
             g_mv=float(g2k.market_value_musd.sum() * 1e6), g_emp=float(g2k.employees.sum()),
             u_n=int(u.companies.sum()), u_val=float(u.valuation_usd.sum()), l_mv=float(fd.market_cap.sum()), l_n=int(fd.companies.sum()))

# ---------- scatter: revenue share vs GDP share (Forbes view & mixed view) ----------
ou = rd(os.path.join(A, 'geography__over_under.csv'))
mixed_rev_total = float(m.revenue_usd.sum())

# ---------- India deep dive ----------
ind = g2k[g2k.iso == 'IND'].sort_values('revenue_musd', ascending=False)
india_firms = [dict(company=r.company, rank=int(r['rank']), sector=r.sector, industry=r.industry_canon,
                    rev=r.revenue_musd * 1e6, prof=r.profits_musd * 1e6, mv=r.market_value_musd * 1e6,
                    emp=None if pd.isna(r.employees) else float(r.employees), city=r.city) for _, r in ind.iterrows()]
india_firms = [{k: (round(v) if isinstance(v, float) else v) for k, v in d.items()} for d in india_firms]
sec_world = g2k.groupby('sector').revenue_musd.sum() / g2k.revenue_musd.sum()
sec_ind = ind.groupby('sector').revenue_musd.sum() / ind.revenue_musd.sum()
india_sectors = [dict(sector=s, india=float(sec_ind.get(s, 0)), world=float(sec_world[s]),
                      n=int((ind.sector == s).sum())) for s in sec_world.sort_values(ascending=False).index]
uni = rd(os.path.join(ROOT, 'startups', 'data', 'unicorns_cbinsights.csv'))
iu = uni[uni.country == 'India'].sort_values('valuation_busd', ascending=False)
india_unicorns = [dict(company=r.company, val=float(r.valuation_busd) * 1e9, city=r.city, industry=r.industry,
                       joined=r.date_joined) for _, r in iu.iterrows()]
# listed universe India
lu = rd(os.path.join(ROOT, 'listed_universe', 'data', 'listed_universe.csv'))
li = lu[lu.country == 'India'].sort_values('market_cap_usd', ascending=False)
india_listed_top = [dict(company=r.company, mv=float(r.market_cap_usd),
                         rev=None if pd.isna(r.revenue_usd) else float(r.revenue_usd)) for _, r in li.head(25).iterrows()]
ex = rd(os.path.join(ROOT, 'stock_market', 'data', 'exchanges.csv'))
ex = ex.sort_values('total_market_cap_usd', ascending=False).reset_index(drop=True)
india_ex = [dict(exchange=r.exchange, rank=int(i) + 1, mv=float(r.total_market_cap_usd), n=int(r.companies), top=r.top_company)
            for i, r in ex.iterrows() if r.exchange_country == 'India']

def rank_of(key):
    vals = sorted(((c.get(key) or 0, c['iso']) for c in C.values()), reverse=True)
    return next(k + 1 for k, (_, i) in enumerate(vals) if i == 'IND')
india_ranks = {k: rank_of(k) for k in ('gdp', 'g_n', 'g_rev', 'g_prof', 'g_mv', 'u_n', 'u_val', 'l_mv')}

PEERS = ['USA', 'CHN', 'JPN', 'DEU', 'GBR', 'FRA', 'IND', 'KOR', 'BRA', 'CAN', 'IDN', 'SAU', 'CHE', 'AUS', 'MEX']
peers = []
for i in PEERS:
    c = C[i]; g = c.get('gdp')
    peers.append(dict(iso=i, name=c['name'], rev_gdp=(c.get('g_rev', 0) / g), mv_gdp=(c.get('g_mv', 0) / g),
                      lmv_gdp=(c.get('l_mv', 0) / g), uni_per_t=(c.get('u_n', 0) / (g / 1e12)),
                      g_per_t=(c.get('g_n', 0) / (g / 1e12)), gdp=g,
                      gdp_pc=(g / c['pop']) if c.get('pop') else None))

# map coverage check against the GeoJSON
geo_ids = set()
gp = os.path.join(ROOT, 'site', 'assets', 'world.geo.js')
if os.path.exists(gp):
    s = open(gp, encoding='utf-8').read()
    geo = json.loads(s[s.index('{'):s.rindex('}') + 1])
    geo_ids = {ft['properties']['name'] for ft in geo['features']}
not_on_map = [c['name'] for c in countries if c['iso'] not in geo_ids and any(k in c for k in ('g_n', 'x_n', 'u_n', 'l_mv'))]

zero_forbes_big = [dict(name=c['name'], gdp=c['gdp']) for c in sorted(C.values(), key=lambda c: -c.get('gdp', 0))
                   if c.get('gdp', 0) > 150e9 and not c.get('g_n')][:12]

data = dict(countries=countries, regions=regions, h2h=h2h, world=world, world_gdp=world_gdp,
            mixed_rev_total=mixed_rev_total, india_firms=india_firms, india_sectors=india_sectors,
            india_unicorns=india_unicorns, india_listed_top=india_listed_top, india_ex=india_ex,
            india_ranks=india_ranks, peers=peers, not_on_map=not_on_map, unmatched_unicorn_countries=unmatched_uni,
            zero_forbes_big=zero_forbes_big, n_exchanges=int(len(ex)))

def clean_json(o):
    if isinstance(o, float):
        return None if (np.isnan(o) or np.isinf(o)) else o
    if isinstance(o, dict): return {k: clean_json(v) for k, v in o.items()}
    if isinstance(o, list): return [clean_json(v) for v in o]
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return clean_json(float(o))
    return o

with open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('/* generated by site/build/geography.py */\nwindow.ATLAS = window.ATLAS || {};\nwindow.ATLAS.geography = ')
    fh.write(json.dumps(clean_json(data), ensure_ascii=False, separators=(',', ':')))
    fh.write(';\n')
print('countries', len(countries), 'not on map:', not_on_map, 'unmatched unicorn countries:', unmatched_uni)
print('india ranks', india_ranks)
print('zero forbes big', [z['name'] for z in zero_forbes_big])
print(os.path.getsize(OUT) // 1024, 'KB')
