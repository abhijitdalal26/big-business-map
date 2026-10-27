"""Build site/data/scale.js for scale.html ("How big is big business?").

Sources: data/global2000_2026.csv (Forbes G2000, FY2024, mkt value May 2025),
data/companies_master.csv (Fortune G500 firms outside Forbes + Forbes largest US private),
listed_universe/data/listed_universe.csv (12.5k listed cos, market cap 2026 snapshot),
data/country_gdp_2024.csv (World Bank GDP 2024).
Run: python site/build/scale.py
"""
import json, math, re
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'site' / 'data' / 'scale.js'

g = pd.read_csv(ROOT / 'data/global2000_2026.csv', encoding='utf-8-sig')
master = pd.read_csv(ROOT / 'data/companies_master.csv', encoding='utf-8-sig')
lu = pd.read_csv(ROOT / 'listed_universe/data/listed_universe.csv', encoding='utf-8-sig')
gdp = pd.read_csv(ROOT / 'data/country_gdp_2024.csv', encoding='utf-8-sig')


def r(x, d=2):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return None
    return round(float(x), d)


def fix_text(s):
    if not isinstance(s, str):
        return s
    for a, b in {'�': 'e'}.items():
        s = s.replace(a, b)
    return s.strip()


def pretty(name):
    name = fix_text(name)
    if not isinstance(name, str):
        return name
    letters = [c for c in name if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.8 and len(name) > 4:
        name = name.title()
        name = re.sub(r"'S\b", "'s", name)
    name = re.sub(r'\s*/[A-Za-z]{2,3}/?$', '', name)  # SEC suffixes like /NEW
    return name


# ---------------------------------------------------------------- regions (<=8)
EUROPE = {'United Kingdom', 'Germany', 'France', 'Switzerland', 'Sweden', 'Italy', 'Spain', 'Norway', 'Poland',
          'Finland', 'Belgium', 'Netherlands', 'Denmark', 'Austria', 'Ireland', 'Portugal', 'Greece', 'Luxembourg',
          'Hungary', 'Czech Republic', 'Romania', 'Bulgaria', 'Iceland', 'Estonia', 'Latvia', 'Lithuania', 'Cyprus',
          'Monaco', 'Liechtenstein', 'Guernsey', 'Jersey', 'Isle of Man', 'Gibraltar', 'Russia', 'Turkey',
          'Kazakhstan', 'Slovakia', 'Slovenia', 'Croatia', 'Malta', 'Ukraine', 'Czechia', 'Serbia'}
MEA = {'Saudi Arabia', 'United Arab Emirates', 'Kuwait', 'Qatar', 'Bahrain', 'Oman', 'Israel', 'Jordan', 'Egypt',
       'South Africa', 'Nigeria', 'Sudan', 'Morocco', 'Kenya', 'Lebanon', 'Iran', 'Iraq'}
AMERICAS = {'Canada', 'Brazil', 'Mexico', 'Argentina', 'Chile', 'Colombia', 'Peru', 'Panama', 'Uruguay',
            'Costa Rica', 'Bahamas', 'Bermuda', 'Cayman Islands', 'Puerto Rico', 'Venezuela'}
REGIONS = ['United States', 'Europe', 'China & HK', 'Japan', 'India', 'Other Asia-Pacific',
           'Middle East & Africa', 'Other Americas']


def region_of(c):
    if c == 'United States': return 'United States'
    if c in ('China', 'Hong Kong', 'Macau'): return 'China & HK'
    if c == 'Japan': return 'Japan'
    if c == 'India': return 'India'
    if c in EUROPE: return 'Europe'
    if c in MEA: return 'Middle East & Africa'
    if c in AMERICAS: return 'Other Americas'
    return 'Other Asia-Pacific'


# ---------------------------------------------------------------- Forbes G2000
g['company'] = g['company'].map(fix_text)
g['rev'] = g.revenue_musd / 1e3   # $B
g['pro'] = g.profits_musd / 1e3
g['ast'] = g.assets_musd / 1e3
g['mv'] = g.market_value_musd / 1e3
SECTORS = g.sector.value_counts().index.tolist()  # by count
forbes = [[row.company, row.country, row.sector, r(row.rev, 2), r(row.pro, 2), r(row.ast, 1), r(row.mv, 2),
           None if pd.isna(row.employees) else int(row.employees), int(row['rank'])]
          for _, row in g.iterrows()]

N = len(g)
tot = dict(rev=g.rev.sum(), pro=g.pro.sum(), ast=g.ast.sum(), mv=g.mv.sum(), emp=g.employees.sum())


def lorenz(vals, npts=200):
    v = np.sort(np.clip(np.asarray(vals, float), 0, None))
    v = v[~np.isnan(v)]
    cum = np.concatenate([[0], np.cumsum(v)]) / v.sum()
    pop = np.linspace(0, 1, len(cum))
    idx = np.unique(np.linspace(0, len(cum) - 1, npts).astype(int))
    gini = 1 - 2 * float(((cum[1:] + cum[:-1]) / 2 * np.diff(pop)).sum())
    return [[r(pop[i] * 100, 2), r(cum[i] * 100, 2)] for i in idx], r(gini, 3)


conc = {}
for key, col in [('rev', 'rev'), ('pro', 'pro'), ('mv', 'mv'), ('ast', 'ast'), ('emp', 'employees')]:
    s = g[col].dropna()
    if key == 'pro':
        s = s[s > 0]
    s = s.sort_values(ascending=False)
    total = s.sum()
    pts, gini = lorenz(s.values)
    cs = s.cumsum() / total
    conc[key] = dict(
        n=int(len(s)), gini=gini, lorenz=pts,
        top={str(k): r(s.head(k).sum() / total * 100, 1) for k in (10, 50, 100, 500)},
        half=int((cs < 0.5).sum() + 1),
        hhi=r(((s / total * 100) ** 2).sum(), 1),
    )

# thresholds: Forbes vs listed universe (revenue)
lu['company'] = lu['company'].map(pretty)
lu_rev = lu[lu.revenue_usd > 0].drop_duplicates('company')
TH = [1, 10, 50, 100, 250, 500]
thresholds = [dict(t=t, forbes=int((g.rev >= t).sum()), listed=int((lu_rev.revenue_usd >= t * 1e9).sum())) for t in TH]

# log histogram of revenue ($B), bins in log10 steps of 0.25 from $10M
edges = np.arange(-2, 3.01, 0.25)
def hist(vals):
    v = np.log10(np.asarray(vals, float)); v = v[np.isfinite(v)]
    c, _ = np.histogram(v, bins=edges)
    return c.tolist()
histo = dict(edges=[r(10 ** e, 4) for e in edges], forbes=hist(g.rev[g.rev > 0]),
             listed=hist(lu_rev.revenue_usd / 1e9))

# Zipf fit on Forbes revenue
zz = g[g.rev > 0].sort_values('rev', ascending=False).reset_index(drop=True)
zz['rk'] = np.arange(1, len(zz) + 1)
def fit(df):
    x = np.log10(df.rk); y = np.log10(df.rev)
    b, a = np.polyfit(x, y, 1)
    yhat = a + b * x
    r2 = 1 - ((y - yhat) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return dict(slope=r(-b, 3), a=r(a, 4), r2=r(r2, 3))
zipf = dict(all=fit(zz), top500=fit(zz.head(500)), top100=fit(zz.head(100)))
# Same on the listed universe (wider, less truncated)
lz = lu_rev.sort_values('revenue_usd', ascending=False).reset_index(drop=True)
lz['rk'] = np.arange(1, len(lz) + 1); lz['rev'] = lz.revenue_usd / 1e9
zipf['listed_top5000'] = fit(lz.head(5000))
zipf_listed_pts = [[int(rk), r(v, 3), n, c] for rk, v, n, c in
                   zip(lz.rk.head(5000), lz.rev.head(5000), lz.company.head(5000), lz.country.head(5000))
                   if rk <= 200 or rk % 5 == 0]

# ---------------------------------------------------------------- true top 100 (revenue, FY2024 basis)
fo = master[master.source.str.contains('Fortune')].copy()
CITY_COUNTRY = {
    'Beijing': 'China', 'Singapore': 'Singapore', 'Moscow': 'Russia', 'St. Petersburg': 'Russia', 'Krasnodar': 'Russia',
    'Paris': 'France', 'St. Denis': 'France', 'Shenzhen': 'China', 'Shanghai': 'China', 'Osaka': 'Japan', 'Tokyo': 'Japan',
    'Mexico City': 'Mexico', 'Prague': 'Czech Republic', 'Jakarta': 'Indonesia', 'Kuala Lumpur': 'Malaysia',
    'Hamburg': 'Germany', 'Frankfurt': 'Germany', 'Stuttgart': 'Germany', 'Karlsruhe': 'Germany',
    'Friedrichshafen': 'Germany', 'Rotterdam': 'Netherlands', 'Utrecht': 'Netherlands', 'Rome': 'Italy',
    'Valencia': 'Spain', 'Zurich': 'Switzerland', 'Doha': 'Qatar', 'Brasilia, Brazil': 'Brazil',
}
def fo_country(city):
    city = fix_text(city) if isinstance(city, str) else ''
    if 'China' in city: return 'China'
    if city in CITY_COUNTRY: return CITY_COUNTRY[city]
    if city.startswith('D') and 'sseldorf' in city: return 'Germany'
    if city.startswith('Gerlingen'): return 'Germany'
    return 'United States'
fo['country'] = fo.notes.map(fo_country)
pv = master[master.source.str.contains('Private \\(US', regex=True)].copy()
own_map = {'State-owned': 'State-owned', 'Private': 'Private', 'Mutual / Cooperative': 'Mutual/co-op',
           'Public (outside Forbes)': 'Listed (not in Forbes)'}
rows = []
for _, x in g.iterrows():
    rows.append(dict(n=x.company, c=x.country, o='Listed (in Forbes)', rev=r(x.rev, 2), pro=r(x.pro, 2), fr=int(x['rank'])))
for _, x in fo.iterrows():
    rows.append(dict(n=fix_text(x.company), c=x.country, o=own_map.get(x.ownership, x.ownership), rev=r(x.revenue_musd / 1e3, 2),
                     pro=r(x.profits_musd / 1e3, 2), fr=None, src='Fortune Global 500'))
for _, x in pv.iterrows():
    rows.append(dict(n=fix_text(x.company), c=x.country, o='Private', rev=r(x.revenue_musd / 1e3, 2), pro=None, fr=None,
                     src='Forbes largest US private'))
tt = pd.DataFrame(rows).dropna(subset=['rev']).sort_values('rev', ascending=False).reset_index(drop=True)
tt['rk'] = np.arange(1, len(tt) + 1)
true100 = tt.head(100)
true_top = true100.where(pd.notnull(true100), None).to_dict('records')
true_summary = dict(
    outside=int((true100.o != 'Listed (in Forbes)').sum()),
    by_type={k: int(v) for k, v in true100.o.value_counts().items()},
    rev_outside=r(true100[true100.o != 'Listed (in Forbes)'].rev.sum(), 0),
    forbes_rank_cut=int(true100[true100.o == 'Listed (in Forbes)'].fr.max()),
)

# ---------------------------------------------------------------- listed universe (market cap)
lm = lu[lu.market_cap_usd > 0].drop_duplicates('company').copy()
lm['region'] = lm.country.fillna('Other').map(region_of)
lm = lm.sort_values('market_cap_usd', ascending=False).reset_index(drop=True)
lm['rk'] = np.arange(1, len(lm) + 1)
total_mc = lm.market_cap_usd.sum()
listed = [[x.company, x.country if isinstance(x.country, str) else '', REGIONS.index(x.region), r(x.market_cap_usd / 1e9, 3),
           r(x.revenue_usd / 1e9, 3) if x.revenue_usd == x.revenue_usd else None] for x in lm.itertuples()]
reg_stats = []
for i, reg in enumerate(REGIONS):
    s = lm[lm.region == reg].market_cap_usd
    reg_stats.append(dict(region=reg, n=int(len(s)), mc=r(s.sum() / 1e12, 2), share=r(s.sum() / total_mc * 100, 1),
                          median=r(s.median() / 1e9, 2), top=lm[lm.region == reg].company.iloc[0]))
mc_thresh = [dict(t=t, n=int((lm.market_cap_usd >= t * 1e9).sum())) for t in (1, 10, 100, 500, 1000)]

MAG7 = ['NVIDIA CORP', 'Apple Inc.', 'Alphabet Inc.', 'Microsoft Corporation', 'Amazon.Com, Inc.', 'Meta Platforms, Inc.', 'Tesla, Inc.']
mag = lm[lm.company.str.lower().isin([m.lower() for m in MAG7])]
tril = lm[lm.market_cap_usd >= 1e12]
mag_mc = mag.market_cap_usd.sum()
bands = [
    ('Magnificent 7', mag_mc),
    ('Other $1T+ club', tril.market_cap_usd.sum() - mag_mc),
    ('Rest of top 100', lm.head(100).market_cap_usd.sum() - tril.market_cap_usd.sum()),
    ('Ranks 101-1,000', lm.iloc[100:1000].market_cap_usd.sum()),
    ('Ranks 1,001-10,000+', lm.iloc[1000:].market_cap_usd.sum()),
]
mcap_bands = [dict(b=b, v=r(v / 1e12, 2), share=r(v / total_mc * 100, 1)) for b, v in bands]
trillion = [dict(n=x.company, c=x.country, mc=r(x.market_cap_usd / 1e12, 3), rev=r(x.revenue_usd / 1e9, 1),
                 mag=x.company in set(mag.company)) for x in tril.itertuples()]

# ---------------------------------------------------------------- people
ge = g.dropna(subset=['employees']).copy()
ge = ge[ge.employees >= 1000]
ge['rpe'] = ge.revenue_musd * 1e6 / ge.employees
ge['ppe'] = ge.profits_musd * 1e6 / ge.employees
people = dict(
    n=int(len(ge)), median_emp=int(g.employees.median()), median_rpe=r(ge.rpe.median(), 0), median_ppe=r(ge.ppe.median(), 0),
    total_emp=int(g.employees.sum()), n_missing=int(g.employees.isna().sum()),
    top10_emp_share=r(g.employees.nlargest(10).sum() / g.employees.sum() * 100, 1),
    india_emp=int(g[g.country == 'India'].employees.sum()),
)
medians = dict(rev=r(g.rev.median(), 2), pro=r(g.pro.median(), 3), ast=r(g.ast.median(), 1), mv=r(g.mv.median(), 2),
               emp=int(g.employees.median()), margin=r((g.profits_musd / g.revenue_musd * 100).median(), 1),
               mean_rev=r(g.rev.mean(), 2), mean_mv=r(g.mv.mean(), 2))

# ---------------------------------------------------------------- profits
g['margin'] = g.profits_musd / g.revenue_musd * 100
loss = g[g.pro < 0]
profit = dict(
    n_loss=int(len(loss)), loss_total=r(loss.pro.sum(), 1), pos_total=r(g[g.pro > 0].pro.sum(), 1),
    top10_profit_share=conc['pro']['top']['10'], margin_blended=r(g.pro.sum() / g.rev.sum() * 100, 2),
    margin_median=medians['margin'],
    n_margin_gt30=int((g.margin > 30).sum()),
)
# margin by sector (median)
sector_margin = (g.groupby('sector').apply(lambda d: pd.Series(dict(
    n=len(d), median=d.margin.median(), blended=d.pro.sum() / d.rev.sum() * 100, loss=(d.pro < 0).sum())))
    .reset_index().sort_values('blended', ascending=False))
sector_margin = [dict(s=x.sector, n=int(x.n), median=r(x['median'], 1), blended=r(x.blended, 1), loss=int(x.loss))
                 for _, x in sector_margin.iterrows()]

# ---------------------------------------------------------------- company vs country
gdp = gdp.dropna(subset=['gdp_usd'])
countries = [dict(n=x.country, v=r(x.gdp_usd / 1e9, 1)) for x in gdp.itertuples()]
n_countries = len(gdp)
gdp_sorted = gdp.sort_values('gdp_usd', ascending=False).reset_index(drop=True)
def gdp_equiv(v_usd):
    """first country with GDP below v, and how many countries are smaller"""
    smaller = gdp_sorted[gdp_sorted.gdp_usd < v_usd]
    bigger = gdp_sorted[gdp_sorted.gdp_usd >= v_usd]
    return dict(n_smaller=int(len(smaller)), just_below=smaller.country.iloc[0] if len(smaller) else None,
                just_above=bigger.country.iloc[-1] if len(bigger) else None, rank=int(len(bigger) + 1))
comp_rev = [dict(n=x.n, c=x.c, v=x.rev, o=x.o) for x in tt.head(60).itertuples()]
comp_mc = [dict(n=x.company, c=x.country, v=r(x.market_cap_usd / 1e9, 1)) for x in lm.head(60).itertuples()]
vivid = []
def add(label, val_usd, kind):
    e = gdp_equiv(val_usd); e.update(label=label, v=r(val_usd / 1e9, 1), kind=kind); vivid.append(e)
for nm in ['Walmart', 'Amazon', 'Reliance Industries', 'State Bank of India', 'Tata Consultancy Services', 'Saudi Aramco']:
    m = g[g.company.str.contains(nm, regex=False)]
    if len(m): add(f'{m.iloc[0].company} revenue (FY2024)', m.iloc[0].revenue_musd * 1e6, 'revenue')
for nm in ['NVIDIA CORP', 'Apple Inc.', 'Microsoft Corporation', 'Reliance Industries', 'HDFC Bank']:
    m = lm[lm.company.str.lower() == nm.lower()]
    if len(m): add(f'{m.iloc[0].company} market cap (2026)', m.iloc[0].market_cap_usd, 'market cap')
world_gdp = gdp.gdp_usd.sum()
india_gdp = float(gdp[gdp.iso3 == 'IND'].gdp_usd.iloc[0])

# India angle
ind = g[g.country == 'India']
india = dict(
    n_forbes=int(len(ind)), rev=r(ind.rev.sum(), 1), pro=r(ind.pro.sum(), 1), mv=r(ind.mv.sum(), 1),
    rev_share=r(ind.rev.sum() / tot['rev'] * 100, 2), mv_share=r(ind.mv.sum() / tot['mv'] * 100, 2),
    top=ind.sort_values('rev', ascending=False).head(5)[['company', 'rev', 'rank']].values.tolist(),
    n_listed=int((lm.country == 'India').sum()), listed_mc=r(lm[lm.country == 'India'].market_cap_usd.sum() / 1e12, 2),
    reliance_rev_rank=int((g.rev > float(ind[ind.company == 'Reliance Industries'].rev.iloc[0])).sum() + 1),
    gdp=r(india_gdp / 1e12, 2),
    n_true100=int((true100.c == 'India').sum()),
    in_true100=true100[true100.c == 'India'].n.tolist(),
)

data = dict(
    sectors=SECTORS, regions=REGIONS,
    forbes_cols=['name', 'country', 'sector', 'revenue_b', 'profit_b', 'assets_b', 'mv_b', 'employees', 'forbes_rank'],
    forbes=forbes,
    totals=dict(rev=r(tot['rev'] / 1e3, 2), pro=r(tot['pro'] / 1e3, 2), ast=r(tot['ast'] / 1e3, 1), mv=r(tot['mv'] / 1e3, 1),
                emp=int(tot['emp']), n_loss=int((g.pro < 0).sum())),
    medians=medians, conc=conc, thresholds=thresholds, histo=histo, zipf=zipf, zipf_listed=zipf_listed_pts,
    true_top=true_top, true_summary=true_summary,
    listed_cols=['name', 'country', 'region_idx', 'mcap_b', 'revenue_b'], listed=listed,
    listed_total_mc=r(total_mc / 1e12, 1), listed_n=int(len(lm)), listed_median_mc=r(lm.market_cap_usd.median() / 1e9, 2),
    reg_stats=reg_stats, mc_thresh=mc_thresh, mcap_bands=mcap_bands, trillion=trillion,
    mag7_share=r(mag_mc / total_mc * 100, 1), mag7_mc=r(mag_mc / 1e12, 1),
    people=people, profit=profit, sector_margin=sector_margin,
    countries=countries, comp_rev=comp_rev, comp_mc=comp_mc, vivid=vivid,
    world_gdp=r(world_gdp / 1e12, 1), n_countries=n_countries, india_gdp=r(india_gdp / 1e12, 2), india=india,
)

js = 'window.ATLAS = window.ATLAS || {};\nwindow.ATLAS.scale = ' + json.dumps(data, separators=(',', ':'), ensure_ascii=False, default=lambda o: None) + ';\n'
js = js.replace('NaN', 'null')
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(js, encoding='utf-8')
print(f'wrote {OUT} ({OUT.stat().st_size/1e6:.2f} MB)')
summary = {k: data[k] for k in ['totals', 'medians', 'thresholds', 'zipf', 'true_summary', 'listed_total_mc', 'listed_n',
                                'listed_median_mc', 'reg_stats', 'mc_thresh', 'mcap_bands', 'mag7_share', 'mag7_mc', 'people',
                                'profit', 'vivid', 'world_gdp', 'india']}
summary['conc'] = {k: {kk: vv for kk, vv in v.items() if kk != 'lorenz'} for k, v in conc.items()}
summary['trillion'] = trillion
summary['true_top20'] = [(x['rk'], x['n'], x['c'], x['o'], x['rev']) for x in true_top[:30]]
summary['sector_margin'] = sector_margin
print(json.dumps(summary, indent=1, default=str))
