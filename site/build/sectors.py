"""Build site/data/sectors.js (window.ATLAS.sectors) from Forbes Global 2000 2025 + World Bank macro.
Run from anywhere:  python site/build/sectors.py
"""
import json, os
import numpy as np, pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
G = pd.read_csv(os.path.join(ROOT, 'data', 'global2000_2026.csv'), encoding='utf-8-sig')
M = pd.read_csv(os.path.join(ROOT, 'data', 'world_macro.csv'), encoding='utf-8-sig')

for c in ['revenue_musd', 'profits_musd', 'market_value_musd', 'assets_musd', 'employees']:
    G[c] = pd.to_numeric(G[c], errors='coerce')

tot = {k: G[k].sum() for k in ['revenue_musd', 'profits_musd', 'market_value_musd', 'assets_musd', 'employees']}


def r(x, d=2):
    if x is None:
        return None
    x = float(x)
    if np.isnan(x) or np.isinf(x):
        return None
    return round(x, d)


def hhi(s):
    s = s[s > 0]
    sh = s / s.sum() * 100
    return float((sh ** 2).sum())


def agg(df):
    rev, pro, mv, ast, emp = (df[k].sum() for k in ['revenue_musd', 'profits_musd', 'market_value_musd', 'assets_musd', 'employees'])
    pos = df[df.profits_musd > 0]
    pe_firm = pos.market_value_musd / pos.profits_musd
    ps_firm = (df.market_value_musd / df.revenue_musd).replace([np.inf], np.nan)
    m = df.profits_musd / df.revenue_musd * 100
    srt = df.revenue_musd.sort_values(ascending=False)
    return dict(
        n=int(len(df)), rev=r(rev, 0), profit=r(pro, 0), mv=r(mv, 0), assets=r(ast, 0), emp=r(emp, 0),
        rev_sh=r(rev / tot['revenue_musd'] * 100), profit_sh=r(pro / tot['profits_musd'] * 100),
        mv_sh=r(mv / tot['market_value_musd'] * 100), emp_sh=r(emp / tot['employees'] * 100),
        agg_margin=r(pro / rev * 100), med_margin=r(m.median()), p10=r(m.quantile(.1)), p25=r(m.quantile(.25)),
        p75=r(m.quantile(.75)), p90=r(m.quantile(.9)), loss_rate=r((df.profits_musd < 0).mean() * 100),
        roa=r(pro / ast * 100), turnover=r(rev / ast, 3),
        ps=r(mv / rev), med_ps=r(ps_firm.median()), pe=r(mv / pro, 1) if pro > 0 else None, med_pe=r(pe_firm.median(), 1),
        hhi=r(hhi(df.revenue_musd), 0), top3=r(srt.head(3).sum() / srt.sum() * 100, 1),
        top3_names=list(df.sort_values('revenue_musd', ascending=False).company.head(3)),
        rev_per_emp=r(rev * 1e6 / emp, 0) if emp else None,
    )


sectors = []
for s, df in G.groupby('sector'):
    a = agg(df); a['sector'] = s; sectors.append(a)
sectors.sort(key=lambda x: -x['rev'])
sector_order = [s['sector'] for s in sectors]

industries = []
for (s, i), df in G.groupby(['sector', 'industry_canon']):
    a = agg(df); a['sector'] = s; a['industry'] = i; industries.append(a)
industries.sort(key=lambda x: -x['rev'])
ind_order = [i['industry'] for i in industries]

# companies (compact rows): name, country, region, sectorIdx, industryIdx, rev, profit, mv, emp, assets, forbesRank
G = G.sort_values('revenue_musd', ascending=False)
comp = []
for _, x in G.iterrows():
    comp.append([x.company, x.country, x.region, sector_order.index(x.sector), ind_order.index(x.industry_canon),
                 r(x.revenue_musd, 0), r(x.profits_musd, 0), r(x.market_value_musd, 0),
                 None if pd.isna(x.employees) else int(x.employees), r(x.assets_musd, 0), int(x['rank'])])

# sector x region
regions = list(G.groupby('region').revenue_musd.sum().sort_values(ascending=False).index)
sxr = []
for (s, rg), df in G.groupby(['sector', 'region']):
    sxr.append([sector_order.index(s), regions.index(rg), r(df.revenue_musd.sum(), 0), r(df.profits_musd.sum(), 0),
                r(df.market_value_musd.sum(), 0), int(len(df))])

# economy vs corporate: map canonical industries to World Bank broad sectors (ISIC: industry = mining, manufacturing, construction, utilities)
INDUSTRY_BUCKET = {
    'Oil & Gas': 'Industry', 'Utilities': 'Industry', 'Materials': 'Industry', 'Chemicals': 'Industry',
    'Construction': 'Industry', 'Consumer Durables': 'Industry', 'Hardware & Equipment': 'Industry',
    'Semiconductors': 'Industry', 'Pharma & Biotech': 'Industry', 'Food, Drink & Tobacco': 'Industry',
    'Capital Goods': 'Industry', 'Aerospace & Defense': 'Industry', 'Engineering & Manufacturing': 'Industry',
    'Automotive': 'Industry', 'Household & Personal Products': 'Industry', 'Conglomerate': 'Industry',
}
G['bucket'] = G.industry_canon.map(INDUSTRY_BUCKET).fillna('Services')
# No Forbes industry is farming. Flag farm-adjacent firms (agribusiness, plantations, fertiliser, seeds) by description keywords.
pat = r'\b(?:plantations?|palm oil|agribusiness|oilseeds?|grains?|crop protection|crop science|fertili[sz]ers?|potash)\b'
agri_kw = G.description.fillna('').str.contains(pat, case=False, regex=True)
agri_firms = G[agri_kw & ~G.sector.isin(['Financials', 'Technology', 'Telecom & Media', 'Healthcare'])]


def wb(code):
    v = M[M.indicator == code].sort_values('year').iloc[-1]
    return float(v.value), int(v.year)


gdp_ag, yr = wb('NV.AGR.TOTL.ZS'); gdp_ind, _ = wb('NV.IND.TOTL.ZS'); gdp_srv, _ = wb('NV.SRV.TOTL.ZS'); gdp_man, _ = wb('NV.IND.MANF.ZS')
emp_ag, eyr = wb('SL.AGR.EMPL.ZS'); emp_ind, _ = wb('SL.IND.EMPL.ZS'); emp_srv, _ = wb('SL.SRV.EMPL.ZS')
gdp, _ = wb('NY.GDP.MKTP.CD'); lab, _ = wb('SL.TLF.TOTL.IN')
bk = G.groupby('bucket')[['revenue_musd', 'profits_musd', 'market_value_musd', 'employees']].sum()
corp = {b: {k: (r(bk.loc[b, c] / bk[c].sum() * 100) if b in bk.index else 0.0)
            for k, c in [('rev', 'revenue_musd'), ('profit', 'profits_musd'), ('mv', 'market_value_musd'), ('emp', 'employees')]}
        for b in ['Agriculture', 'Industry', 'Services']}
gsum = gdp_ag + gdp_ind + gdp_srv
economy = dict(
    year=yr, emp_year=eyr, gdp_usd=gdp, labour_force=lab,
    gdp_share_raw={'Agriculture': r(gdp_ag), 'Industry': r(gdp_ind), 'Services': r(gdp_srv)},
    gdp_share={'Agriculture': r(gdp_ag / gsum * 100), 'Industry': r(gdp_ind / gsum * 100), 'Services': r(gdp_srv / gsum * 100)},
    manufacturing=r(gdp_man),
    emp_share={'Agriculture': r(emp_ag), 'Industry': r(emp_ind), 'Services': r(emp_srv)},
    corp=corp,
    agri_workers=r(emp_ag / 100 * lab, 0),
    agri_adjacent=[[x.company, x.country, x.industry_canon, r(x.revenue_musd, 0)]
                   for _, x in agri_firms.sort_values('revenue_musd', ascending=False).head(15).iterrows()],
    agri_adjacent_n=int(len(agri_firms)), agri_adjacent_rev=r(agri_firms.revenue_musd.sum(), 0),
    agri_adjacent_emp=r(agri_firms.employees.sum(), 0),
    mapping=INDUSTRY_BUCKET,
    series={code: [[int(y), r(v)] for y, v in M[M.indicator == code][['year', 'value']].values]
            for code in ['NV.AGR.TOTL.ZS', 'NV.IND.TOTL.ZS', 'NV.SRV.TOTL.ZS', 'SL.AGR.EMPL.ZS', 'SL.IND.EMPL.ZS', 'SL.SRV.EMPL.ZS']},
)

# sector mix by country (top 20 countries by revenue + India)
top_c = list(G.groupby('country').revenue_musd.sum().sort_values(ascending=False).head(20).index)
if 'India' not in top_c:
    top_c.append('India')
cmix = {}
for c in top_c:
    df = G[G.country == c]
    s = df.groupby('sector').revenue_musd.sum()
    cmix[c] = dict(n=int(len(df)), rev=r(df.revenue_musd.sum(), 0),
                   mix=[r(s.get(sec, 0) / s.sum() * 100) for sec in sector_order])

meta = dict(
    total=dict(n=int(len(G)), rev=r(tot['revenue_musd'], 0), profit=r(tot['profits_musd'], 0), mv=r(tot['market_value_musd'], 0),
               emp=r(tot['employees'], 0), emp_missing=int(G.employees.isna().sum()), loss_makers=int((G.profits_musd < 0).sum()),
               med_margin=r((G.profits_musd / G.revenue_musd * 100).median()), hhi_all=r(hhi(G.revenue_musd), 0)),
    sectors=sector_order, industries=ind_order, regions=regions,
)
out = dict(meta=meta, sectors=sectors, industries=industries, companies=comp, sxr=sxr, economy=economy, cmix=cmix)
js = 'window.ATLAS = window.ATLAS || {};\nwindow.ATLAS.sectors = ' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';\n'
p = os.path.join(ROOT, 'site', 'data', 'sectors.js')
with open(p, 'w', encoding='utf-8') as f:
    f.write(js)
print('wrote', p, len(js) // 1024, 'KB')
