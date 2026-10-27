"""Build site/data/time.js -> window.ATLAS.time
Decade view from Forbes Global 2000 10-year history (2016-2025, approximate fiscal years) + World Bank macro."""
import json, os
import pandas as pd, numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
D = os.path.join(ROOT, 'data')
OUT = os.path.join(ROOT, 'site', 'data', 'time.js')
h = pd.read_csv(os.path.join(D, 'global2000_2026_history.csv'), encoding='utf-8-sig')
g = pd.read_csv(os.path.join(D, 'global2000_2026.csv'), encoding='utf-8-sig')
wm = pd.read_csv(os.path.join(D, 'world_macro.csv'), encoding='utf-8-sig')
YRS = list(range(2016, 2026))

meta = g.set_index('company')[['rank', 'country', 'region', 'sector', 'industry_canon', 'market_value_musd']]
W = {m: h[h.metric == m].pivot_table(index='company', columns='approx_year', values='value', aggfunc='first').reindex(columns=YRS)
     for m in ['revenue', 'profits', 'assets', 'employees']}
rev, prof, emp = W['revenue'], W['profits'], W['employees']

# glitch filter: unit errors show up as >15x year-on-year jumps in revenue or assets
def glitchy(df):
    r = df.div(df.shift(axis=1)).iloc[:, 1:]
    return ((r > 15) | (r < 1 / 15)).any(axis=1)
bad = set(rev.index[glitchy(rev.where(rev > 0))]) | set(W['assets'].index[glitchy(W['assets'].where(W['assets'] > 0))])
prof = prof.reindex(rev.index)
full = rev.notna().all(axis=1) & prof.notna().all(axis=1) & (rev > 0).all(axis=1)
cohort = [c for c in rev.index[full] if c not in bad and c in meta.index]
print('cohort', len(cohort), 'excluded glitch', len(bad))
R, Pf = rev.loc[cohort], prof.loc[cohort]
M = meta.loc[cohort]

def r1(x): return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 1)
tot = dict(year=YRS, rev=[r1(R[y].sum()) for y in YRS], profit=[r1(Pf[y].sum()) for y in YRS],
           margin=[r1(Pf[y].sum() / R[y].sum() * 100) for y in YRS],
           med_margin=[r1((Pf[y] / R[y] * 100).median()) for y in YRS])
A = W['assets'].reindex(cohort); ac = A.notna().all(axis=1)
tot['assets'] = [r1(A[ac][y].sum()) for y in YRS]
E = emp.reindex(cohort); ec = E[[2018, 2025]].notna().all(axis=1) & E.loc[:, 2018:2025].notna().all(axis=1)
tot['emp'] = [None if y < 2018 else r1(E[ec][y].sum()) for y in YRS]
tot['n'] = len(cohort); tot['n_assets'] = int(ac.sum()); tot['n_emp'] = int(ec.sum())
tot['rev_per_emp'] = [None if y < 2018 else r1(R[ec][y].sum() / E[ec][y].sum() * 1e6) for y in YRS]
# unbalanced panel (everyone with data that year) — shows composition / survivorship effect
panel = dict(rev=[r1(rev[y].sum()) for y in YRS], n=[int(rev[y].notna().sum()) for y in YRS])

# groups
def grp_series(key, keep=None):
    out = {}
    for k, idx in M.groupby(key).groups.items():
        if keep and k not in keep: continue
        out[k] = dict(n=len(idx), rev=[r1(R.loc[idx, y].sum()) for y in YRS], profit=[r1(Pf.loc[idx, y].sum()) for y in YRS])
    return out
top_c = M.assign(r=R[2025]).groupby('country').r.sum().sort_values(ascending=False)
keepc = list(top_c.index[:14]) + [c for c in ['India', 'Saudi Arabia', 'Brazil'] if c not in top_c.index[:14]]
groups = dict(sector=grp_series('sector'), region=grp_series('region'), country=grp_series('country', keepc))
cagr_country = []
for c, d in M.assign(a=R[2016], b=R[2025], pa=Pf[2016], pb=Pf[2025]).groupby('country'):
    if len(d) < 8: continue
    cagr_country.append(dict(country=c, n=len(d), rev15=r1(d.a.sum()), rev24=r1(d.b.sum()),
                             cagr=r1(((d.b.sum() / d.a.sum()) ** (1 / 9) - 1) * 100),
                             pcagr=r1(((d.pb.sum() / d.pa.sum()) ** (1 / 9) - 1) * 100) if d.pa.sum() > 0 and d.pb.sum() > 0 else None))
cagr_country.sort(key=lambda r: -r['cagr'])

# company movers
cm = pd.DataFrame(dict(rev15=R[2016], rev24=R[2025], p15=Pf[2016], p24=Pf[2025])).join(M)
cm['growth'] = (cm.rev24 / cm.rev15 - 1) * 100
cm['abs'] = cm.rev24 - cm.rev15
big = cm[cm.rev15 >= 5000]
def rows(d):
    return [dict(company=i, country=r.country, sector=r.sector, industry=r.industry_canon, rank=int(r['rank']), rev15=r1(r.rev15), rev24=r1(r.rev24),
                 growth=r1(r.growth), abs=r1(r['abs']), p15=r1(r.p15), p24=r1(r.p24)) for i, r in d.iterrows()]
movers = dict(all=rows(big.sort_values('growth', ascending=False)), n_big=len(big),
              shrank_pct=r1((cm.growth < 0).mean() * 100), median_growth=r1(cm.growth.median()),
              shrank_big_pct=r1((big.growth < 0).mean() * 100))

# bump chart: rank within cohort
def bump(df):
    rk = df.rank(ascending=False, method='first')
    top = rk[2025].sort_values().index[:20]
    return [dict(company=c, sector=M.loc[c, 'sector'], country=M.loc[c, 'country'], rank=[int(rk.loc[c, y]) for y in YRS],
                 val=[r1(df.loc[c, y]) for y in YRS]) for c in top]
bumps = dict(rev=bump(R), profit=bump(Pf))

# profit pool migration
def pool(key):
    out = []
    a = (Pf[2016] + Pf[2017]) / 2; b = (Pf[2024] + Pf[2025]) / 2
    ra = (R[2016] + R[2017]) / 2; rb = (R[2024] + R[2025]) / 2
    for k, idx in M.groupby(key).groups.items():
        out.append(dict(name=k, n=len(idx), p_start=r1(a[idx].sum()), p_end=r1(b[idx].sum()),
                        ps_start=r1(a[idx].sum() / a.sum() * 100), ps_end=r1(b[idx].sum() / b.sum() * 100),
                        rs_start=r1(ra[idx].sum() / ra.sum() * 100), rs_end=r1(rb[idx].sum() / rb.sum() * 100)))
    for r in out:
        r['pp'] = round(r['ps_end'] - r['ps_start'], 2); r['rpp'] = round(r['rs_end'] - r['rs_start'], 2)
    return sorted(out, key=lambda r: r['pp'])
pools = dict(sector=pool('sector'), industry=pool('industry_canon'))

# sector shares over time
sectors = M.assign(r=R[2025]).groupby('sector').r.sum().sort_values(ascending=False).index.tolist()
shares = dict(sectors=sectors,
              rev={s: [r1(R.loc[M.sector == s, y].sum() / R[y].sum() * 100) for y in YRS] for s in sectors},
              profit={s: [r1(Pf.loc[M.sector == s, y].sum() / Pf[y].sum() * 100) for y in YRS] for s in sectors})
mv_now = g.groupby('sector').market_value_musd.sum()
tech_mv_share = r1(mv_now['Technology'] / mv_now.sum() * 100)
mv_share_now = {s: r1(mv_now[s] / mv_now.sum() * 100) for s in mv_now.index}

# productivity by sector: 2018 -> 2025, firms with employees
prod = []
for s in sectors:
    idx = [c for c in M.index[M.sector == s] if ec.get(c, False)]
    if len(idx) < 5: continue
    e0, e1 = E.loc[idx, 2018].sum(), E.loc[idx, 2025].sum(); r0, r1_ = R.loc[idx, 2018].sum(), R.loc[idx, 2025].sum()
    prod.append(dict(sector=s, n=len(idx), emp17=r1(e0), emp24=r1(e1), rev17=r1(r0), rev24=r1(r1_),
                     emp_g=r1((e1 / e0 - 1) * 100), rev_g=r1((r1_ / r0 - 1) * 100),
                     rpe17=r1(r0 / e0 * 1e6), rpe24=r1(r1_ / e1 * 1e6)))

# macro
def wmi(code): return {int(r.year): float(r.value) for r in wm[wm.indicator == code].itertuples()}
gdp, ldom = wmi('NY.GDP.MKTP.CD'), wmi('CM.MKT.LDOM.NO')
def wb(path, iso='WLD'):
    js = json.load(open(path)); rows_ = js[1] if isinstance(js, list) else js
    return {int(r['date']): r['value'] for r in rows_ if r['countryiso3code'] == iso and r['value'] is not None}
BC = os.path.join(ROOT, 'site', 'build')
mcap = wb(os.path.join(BC, 'raw_context', 'wb_CM.MKT.LCAP.CD.json'))
mcap_gdp = wb(os.path.join(BC, 'cache', 'wb_CM.MKT.LCAP.GD.ZS.json'))
ldjs = json.load(open(os.path.join(BC, 'raw_context', 'wb_CM.MKT.LDOM.NO.json')))[1]
LC = {'USA': 'United States', 'CHN': 'China', 'IND': 'India', 'JPN': 'Japan', 'GBR': 'United Kingdom', 'KOR': 'South Korea', 'DEU': 'Germany', 'CAN': 'Canada'}
listed_by = {}
for r in ldjs:
    if r['countryiso3code'] in LC and r['value'] is not None:
        listed_by.setdefault(LC[r['countryiso3code']], {})[int(r['date'])] = r['value']
my = list(range(2000, 2025))
macro = dict(year=my, gdp=[gdp.get(y) for y in my], listed=[ldom.get(y) for y in my],
             mcap=[mcap.get(y) for y in my], mcap_gdp=[r1(mcap_gdp.get(y)) for y in my],
             listed_by={k: [v.get(y) for y in range(1996, 2025)] for k, v in listed_by.items()}, listed_years=list(range(1996, 2025)))

H = dict(n=len(cohort), rev_x=round(tot['rev'][-1] / tot['rev'][0], 2), prof_x=round(tot['profit'][-1] / tot['profit'][0], 2),
         rev_cagr=r1(((tot['rev'][-1] / tot['rev'][0]) ** (1 / 9) - 1) * 100), prof_cagr=r1(((tot['profit'][-1] / tot['profit'][0]) ** (1 / 9) - 1) * 100),
         m15=tot['margin'][0], m24=tot['margin'][-1], m20=tot['margin'][5],
         gdp_x=round(gdp[2024] / gdp[2016], 2), tech_mv_share=tech_mv_share,
         tech_p15=shares['profit']['Technology'][0], tech_p24=shares['profit']['Technology'][-1],
         tech_r15=shares['rev']['Technology'][0], tech_r24=shares['rev']['Technology'][-1],
         panel_x=round(panel['rev'][-1] / panel['rev'][0], 2), entrants=2000 - len(cohort), excluded=len(bad))
data = dict(H=H, years=YRS, tot=tot, panel=panel, groups=groups, cagr_country=cagr_country, movers=movers, bumps=bumps, pools=pools,
            shares=shares, mv_share_now=mv_share_now, prod=prod, macro=macro)
js = 'window.ATLAS = window.ATLAS || {};\nwindow.ATLAS.time = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':'), default=float).replace('NaN', 'null') + ';\n'
open(OUT, 'w', encoding='utf-8').write(js)
print('wrote', round(len(js) / 1024), 'KB'); print(json.dumps(H, indent=1))
print(pools['sector'][:3], pools['sector'][-3:]); print(cagr_country[:5], [c for c in cagr_country if c['country'] == 'India'])
print(prod); print(movers['all'][:5])
