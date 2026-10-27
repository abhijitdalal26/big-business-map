"""Build site/data/context.js (window.ATLAS.context) + clean CSVs in site/build/context_data/.

Inputs (all saved under site/build/raw_context/):
  wb_*.json                      World Bank API downloads (run fetch_wb_context.py first)
  ilo2.csv                       ILOSTAT SDMX DF_EMP_NIFL_SEX_RT (informal employment rate, harmonized)
  ilo_world_profile.txt          ILO "World informality regional statistical profile" (2025) text
  kpmg_q4_2025.txt               KPMG Venture Pulse Q4'25 text (PitchBook data)
  ey_ipo_q3_2026.txt             EY Global IPO Trends Q3 2026 text (Dealogic data)
  xbma_2025.txt                  XBMA Annual Review 2025 text (LSEG data)
  wcm_2025.txt                   World Cooperative Monitor 2025 executive summary text
  wiki_market_cap_list.html      Wikipedia list of public corporations by market cap (trillion-dollar table)
  globalswf_ranking.html         Global SWF ranking page
Curated numbers transcribed from those files (and from web articles cited inline) are kept in this script
with source name + URL + date, and written out as CSV so every figure can be traced.
"""
import json, os, re, datetime
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw_context')
OUT = os.path.join(HERE, 'context_data')
SITE = os.path.dirname(HERE)
os.makedirs(OUT, exist_ok=True)

WB_URL = 'https://data.worldbank.org/indicator/{}'

# ---------------------------------------------------------------- World Bank helpers
countries = json.load(open(os.path.join(RAW, 'wb_countries.json')))[1]
REAL = {c['id']: c['name'] for c in countries if c['region']['id'] != 'NA'}
REGION = {c['id']: c['region']['value'].strip() for c in countries if c['region']['id'] != 'NA'}
INCOME = {c['id']: c['incomeLevel']['value'].strip() for c in countries if c['region']['id'] != 'NA'}


def wb(ind):
    js = json.load(open(os.path.join(RAW, f'wb_{ind}.json')))
    rows = [{'iso3': r['countryiso3code'], 'name': r['country']['value'], 'year': int(r['date']), 'value': r['value']}
            for r in js[1] if r['value'] is not None and r['countryiso3code']]
    return pd.DataFrame(rows)


def series(df, iso, y0=None, y1=None):
    s = df[df.iso3 == iso].sort_values('year')
    if y0: s = s[s.year >= y0]
    if y1: s = s[s.year <= y1]
    return {int(y): float(v) for y, v in zip(s.year, s.value)}


def save(name, df):
    df.to_csv(os.path.join(OUT, name), index=False, encoding='utf-8')


C = {}  # the payload

# ================================================================ 1. Pyramid of business
UNI_N = 1442
pyr = [
    dict(layer='All micro, small & medium firms incl. informal (estimate)', n=400e6, label='375–450 million',
         note='McKinsey study for IFC (2010): 375–450M MSMEs worldwide, majority informal. Midpoint ~400M plotted.',
         source='IFC/McKinsey via CGAP, "Counting SMEs and their demand for financing"', url='https://www.cgap.org/blog/counting-smes-and-their-demand-for-financing', year='2010 estimate'),
    dict(layer='Formal (registered) MSMEs', n=322e6, label='322 million+',
         note='IFC MSME Economic Indicators: >322M formal MSMEs employing >705M people (data to 2019).',
         source='IFC / SME Finance Forum, MSME Economic Indicators', url='https://www.smefinanceforum.org/data-sites/msme-country-indicators', year='2019'),
    dict(layer='Listed companies (domestic, all exchanges)', n=47980, label='47,980',
         note='World Bank / WFE count of listed domestic companies, end-2024 (2025 figure distorted by an India data jump — see caveat).',
         source='World Bank, CM.MKT.LDOM.NO', url=WB_URL.format('CM.MKT.LDOM.NO'), year='2024'),
    dict(layer='Forbes Global 2000', n=2000, label='2,000', note='The 2,000 largest listed companies by a mix of sales, profit, assets and market value.',
         source='Forbes Global 2000 (2025)', url='https://www.forbes.com/lists/global2000/', year='2025'),
    dict(layer='Unicorns (private, valued $1B+)', n=UNI_N, label=f'{UNI_N:,}', note='Private VC-backed companies valued at $1B+ (CB Insights unicorn board, as collected for this project).',
         source='CB Insights Unicorn Board', url='https://www.cbinsights.com/research-unicorn-companies', year='2025'),
    dict(layer='Fortune Global 500', n=500, label='500', note='Largest companies by revenue, listed or not (includes state firms and co-ops).',
         source='Fortune Global 500 (2025)', url='https://fortune.com/ranking/global500/', year='2025'),
    dict(layer='Companies that ever crossed $1 trillion market value', n=19, label='19', note='Includes PetroChina (2007) and 2026 entrants (SpaceX, Walmart, Samsung, Micron, SK Hynix, AMD).',
         source='Wikipedia, List of public corporations by market capitalization (trillion-dollar table)', url='https://en.wikipedia.org/wiki/List_of_public_corporations_by_market_capitalization', year='as of Oct 2026'),
]
C['pyramid'] = pyr
save('pyramid_of_business.csv', pd.DataFrame(pyr))

# who employs the world: ILO status in employment (modelled, latest year in chart) - from ILO profile page 1
ilo_profile_url = 'https://www.ilo.org/sites/default/files/2025-05/World_Informality%20Regional%20statistical%20profile.pdf'
txt = open(os.path.join(RAW, 'ilo_world_profile.txt'), encoding='utf-8').read()
def grab(pat):
    m = re.search(pat, re.sub(r'\s+', ' ', txt))
    return float(m.group(1)) if m else None
emp = dict(employees=grab(r'World \(Employees\), ([\d.]+)'), employers=grab(r'World \(Employers\), ([\d.]+)'),
           own=grab(r'World \(Own- account workers\), ([\d.]+)'))
emp['family'] = round(100 - emp['employees'] - emp['employers'] - emp['own'], 1)
C['employment_status'] = [
    dict(status='Employees (wage & salaried)', pct=emp['employees']),
    dict(status='Own-account workers (self-employed, no staff)', pct=emp['own']),
    dict(status='Contributing family workers', pct=emp['family']),
    dict(status='Employers', pct=emp['employers']),
]
C['employment_status_src'] = dict(source='ILO modelled estimates, in ILO "World — informality regional statistical profile" (2025)', url=ilo_profile_url, year='latest (c.2022)')
save('world_employment_by_status.csv', pd.DataFrame(C['employment_status']).assign(source=C['employment_status_src']['source'], url=ilo_profile_url))

# self-employment share (WB / ILO modelled) - panel for dropdown
se = wb('SL.EMP.SELF.ZS')
se_c = se[se.iso3.isin(list(REAL) + ['WLD'])]
C['selfemp'] = {iso: series(se_c, iso, 1991) for iso in sorted(se_c.iso3.unique())}
C['selfemp_names'] = {iso: (REAL.get(iso) or 'World') for iso in C['selfemp']}
save('self_employment_share_wb.csv', se_c.assign(source='World Bank SL.EMP.SELF.ZS (ILO modelled)', url=WB_URL.format('SL.EMP.SELF.ZS')))

# ================================================================ 2. Formal vs informal
inf_income = [dict(group='World', pct=grab(r'World, ([\d.]+) World: High')), dict(group='Low income', pct=grab(r'World: Low income, ([\d.]+)')),
              dict(group='Lower-middle income', pct=grab(r'World: Lower-middle income, ([\d.]+)')),
              dict(group='Upper-middle income', pct=grab(r'World: Upper-middle income, ([\d.]+)')), dict(group='High income', pct=grab(r'World: High income, ([\d.]+)'))]
# informal enterprises share (2019 snapshot, ILO 2023) - transcribed from profile page 2 chart labels
inf_ent = [dict(group='World', pct=83.9), dict(group='Low income', pct=93.6), dict(group='Lower-middle income', pct=90.3),
           dict(group='Upper-middle income', pct=76.1), dict(group='High income', pct=52.0)]
for a, b in zip(inf_income, inf_ent):
    a['ent_pct'] = b['pct']
C['informal_income'] = inf_income
C['informal_income_src'] = dict(source='ILO modelled estimates (informal employment, 2024) and ILO 2023 statistical update (informal enterprises, 2019)', url=ilo_profile_url)
save('informal_by_income_group.csv', pd.DataFrame(inf_income).rename(columns={'pct': 'informal_employment_pct_2024', 'ent_pct': 'informal_enterprises_pct_2019'}).assign(source=C['informal_income_src']['source'], url=ilo_profile_url))

ilo = pd.read_csv(os.path.join(RAW, 'ilo2.csv'), low_memory=False)
ilo = ilo[(ilo.SEX == 'SEX_T') & (~ilo.TIME_PERIOD.astype(str).str.contains('Q|M'))].copy()
ilo['year'] = ilo.TIME_PERIOD.astype(int)
ilo = ilo[ilo.year >= 2015].sort_values('year').groupby('REF_AREA').tail(1)
gdp = wb('NY.GDP.MKTP.CD')
gdp_l = gdp[gdp.iso3.isin(REAL)].sort_values('year').groupby('iso3').tail(1).set_index('iso3').value
inf_c = pd.DataFrame({'iso3': ilo.REF_AREA, 'name': ilo.REF_AREA.map(REAL), 'year': ilo.year, 'pct': ilo.OBS_VALUE.round(1),
                      'survey': ilo.SOURCE.astype(str).str.encode('latin1', 'ignore').str.decode('ascii', 'ignore')})
inf_c = inf_c.dropna(subset=['name'])
inf_c['region'] = inf_c.iso3.map(REGION)
inf_c['gdp_busd'] = inf_c.iso3.map(gdp_l / 1e9).round(0)
C['informal_country'] = inf_c.sort_values('pct', ascending=False).to_dict('records')
C['informal_country_src'] = dict(source='ILOSTAT, informal employment rate (harmonized series, DF_EMP_NIFL_SEX_RT), latest annual value 2015+', url='https://ilostat.ilo.org/topics/informality/')
save('informal_employment_by_country_ilostat.csv', inf_c.assign(source=C['informal_country_src']['source'], url='https://sdmx.ilo.org/rest/data/ILO,DF_EMP_NIFL_SEX_RT/'))

# ================================================================ 3. Business creation
nd = wb('IC.BUS.NDNS.ZS'); nr = wb('IC.BUS.NREG')
nd_c = nd[nd.iso3.isin(list(REAL) + ['WLD'])]
C['newbiz'] = {iso: series(nd_c, iso) for iso in sorted(nd_c.iso3.unique())}
C['newbiz_reg'] = {iso: series(nr, iso) for iso in sorted(nr[nr.iso3.isin(REAL)].iso3.unique())}
C['names'] = {iso: n for iso, n in REAL.items()}; C['names']['WLD'] = 'World'
C['regions'] = REGION
lat = nd_c[nd_c.iso3.isin(REAL) & (nd_c.year >= 2020)].sort_values('year').groupby('iso3').tail(1)
regs = nr.set_index(['iso3', 'year']).value
lat = lat.assign(regs=[regs.get((i, y)) for i, y in zip(lat.iso3, lat.year)], region=lat.iso3.map(REGION))
C['newbiz_latest'] = lat.rename(columns={'value': 'density'}).round({'density': 2}).sort_values('density', ascending=False).to_dict('records')
save('new_business_density_wb.csv', nd_c.merge(nr[['iso3', 'year', 'value']].rename(columns={'value': 'new_registrations'}), on=['iso3', 'year'], how='left')
     .rename(columns={'value': 'new_business_density_per_1000_working_age'}).assign(source='World Bank Entrepreneurship Database (IC.BUS.NDNS.ZS, IC.BUS.NREG)', url=WB_URL.format('IC.BUS.NDNS.ZS')))

# ================================================================ 4. Venture capital (KPMG Venture Pulse Q4'25, PitchBook)
kp = open(os.path.join(RAW, 'kpmg_q4_2025.txt'), encoding='utf-8').read().split('\n')
def kpmg_quarters(title):
    i = next(k for k, l in enumerate(kp) if l.strip() == title)
    vals = []
    for l in kp[i + 1:i + 60]:
        m = re.fullmatch(r'\$([\d.]+)', l.strip())
        if m: vals.append(float(m.group(1)))
        if len(vals) == 28: break
    return vals
def annual(q): return [round(sum(q[i * 4:(i + 1) * 4]), 1) for i in range(7)]
glob_q = None
for k, l in enumerate(kp):
    if l.strip() == 'Global venture financing':
        glob_q = [float(x[1:]) for x in kp[k + 2:k + 30]]; break
reg = {'Global': annual(glob_q), 'Americas': annual(kpmg_quarters('Venture financing in the Americas')),
       'Europe': annual(kpmg_quarters('Venture financing in Europe')), 'Asia': annual(kpmg_quarters('Venture financing in Asia')),
       'China': annual(kpmg_quarters('Venture financing in China')), 'India': annual(kpmg_quarters('Venture financing in India'))}
# US: chart on p.22 lists 27 quarters + Q4'25 ($91.15)
i = kp.index('Billions keep flowing towards AI, unchecked')
usq = [float(l.strip()[1:]) for l in kp[i + 1:i + 40] if re.fullmatch(r'\$[\d.]+', l.strip())][:28]
reg['US'] = annual(usq)
years = list(range(2019, 2026))
vc = []
for j, y in enumerate(years):
    r = {k: v[j] for k, v in reg.items()}
    vc.append(dict(year=y, global_=r['Global'], us=r['US'], rest_americas=round(r['Americas'] - r['US'], 1), europe=r['Europe'],
                   china=r['China'], india=r['India'], rest_asia=round(r['Asia'] - r['China'] - r['India'], 1),
                   rest_world=round(r['Global'] - r['Americas'] - r['Europe'] - r['Asia'], 1)))
assert abs(vc[-2]['global_'] - 391.9) < 0.5, vc[-2]
C['vc'] = vc
C['vc_src'] = dict(source="KPMG Private Enterprise, Venture Pulse Q4'25 (data: PitchBook, 19 Jan 2026); annual = sum of quarterly deal value", url='https://kpmg.com/kpmg-us/content/dam/kpmg/pdf/2026/venture-pulse-q4-2025.pdf')
save('vc_by_region_kpmg_pitchbook.csv', pd.DataFrame(vc).rename(columns={'global_': 'global'}).assign(unit='USD bn', source=C['vc_src']['source'], url=C['vc_src']['url']))

CB = 'https://news.crunchbase.com/venture/funding-data-third-largest-year-2025/'
vc_ai = [
    dict(period='2023', total=304, ai=55.6, src='Crunchbase News, year-end 2024 analysis', url='https://news.crunchbase.com/venture/global-funding-data-analysis-ai-eoy-2024/'),
    dict(period='2024', total=328, ai=114, src='Crunchbase News, year-end 2025 analysis (7 Jan 2026)', url=CB),
    dict(period='2025', total=425, ai=211, src='Crunchbase News, year-end 2025 analysis (7 Jan 2026)', url=CB),
    dict(period='Q3 2026', total=159, ai=102, src='Crunchbase News, Q3 2026 global funding (5 Oct 2026)', url='https://news.crunchbase.com/venture/q3-2026-global-startup-funding-ai-billion-dollar-rounds-exits-data/'),
]
for r in vc_ai: r['share'] = round(100 * r['ai'] / r['total'], 1); r['non_ai'] = round(r['total'] - r['ai'], 1)
C['vc_ai'] = vc_ai
save('vc_ai_share_crunchbase.csv', pd.DataFrame(vc_ai).assign(unit='USD bn'))
C['vc_2026'] = dict(ytd=679, q1=308, q2=212, q3=159, h1=510, fy2025_revised=440, us_q3=91,
                    src='Crunchbase News (H1 2026 report 2 Jul 2026; Q3 2026 report 5 Oct 2026)',
                    url='https://news.crunchbase.com/venture/q3-2026-global-startup-funding-ai-billion-dollar-rounds-exits-data/',
                    url_h1='https://news.crunchbase.com/venture/global-startup-exits-ipo-ma-soar-ai-q2-h1-2026/')

# ================================================================ 5. IPOs (EY Global IPO Trends, Dealogic)
EY26 = 'https://www.ey.com/content/dam/ey-unified-site/ey-com/en-gl/insights/ipo/documents/ey-gl-global-ipo-trends-report-q3-10-2026.pdf'
ipo = [
    dict(period='2021', count=2388, proceeds=453.3, src='EY Global IPO Trends Q4 2021 (press release, Dec 2021; deals to 7 Dec + expected)', url='https://ey.com/en_sg/news/2021/12/global-ipo-market-has-record-breaking-2021-prepare-for-headwinds-in-2022'),
    dict(period='2022', count=1415, proceeds=184, src='EY Global IPO Trends Q3 2026 (Oct 2026)', url=EY26),
    dict(period='2023', count=1351, proceeds=126, src='EY Global IPO Trends Q3 2026 (Oct 2026)', url=EY26),
    dict(period='2024', count=1240, proceeds=123, src='EY Global IPO Trends Q3 2026 (Oct 2026)', url=EY26),
    dict(period='2025', count=1340, proceeds=187, src='EY Global IPO Trends Q3 2026 (Oct 2026)', url=EY26),
    dict(period='Jan–Sep 2025', count=922, proceeds=114, src='EY Global IPO Trends Q3 2026 (Oct 2026)', url=EY26),
    dict(period='Jan–Sep 2026', count=908, proceeds=290, src='EY Global IPO Trends Q3 2026 (Oct 2026); includes ~$86B from one June 2026 IPO', url=EY26),
]
C['ipo'] = ipo
save('ipo_global_ey.csv', pd.DataFrame(ipo).assign(unit_proceeds='USD bn'))
ipo_dest = [  # number of IPOs by listing destination, EY Q3 2026 report p.3 & p.9
    dict(market='India', n2025=379, n2026=240), dict(market='Chinese Mainland', n2025=137, n2026=131),
    dict(market='Hong Kong', n2025=114, n2026=115), dict(market='United States', n2025=216, n2026=97),
    dict(market='Malaysia', n2025=54, n2026=38)]
C['ipo_dest'] = ipo_dest
C['ipo_dest_proceeds_2026'] = [dict(market='United States', busd=164), dict(market='Hong Kong', busd=50), dict(market='Chinese Mainland', busd=37),
                              dict(market='India', busd=12), dict(market='Netherlands', busd=4)]
save('ipo_top_destinations_ey.csv', pd.DataFrame(ipo_dest).merge(pd.DataFrame(C['ipo_dest_proceeds_2026']).rename(columns={'busd': 'proceeds_busd_jan_sep_2026'}), on='market', how='left')
     .rename(columns={'n2025': 'ipos_2025', 'n2026': 'ipos_jan_sep_2026'}).assign(source='EY Global IPO Trends Q3 2026 (Dealogic)', url=EY26))

# ================================================================ 6. M&A (XBMA Annual Review 2025, LSEG; inflation-adjusted 2025 $)
ma_vals = [4544, 5734, 4689, 4385, 5084, 4766, 4347, 6763, 3780, 3064, 3166, 4600]
C['ma'] = [dict(year=2014 + i, busd=v) for i, v in enumerate(ma_vals)]
C['ma_src'] = dict(source='XBMA Annual Review for 2025 (Harvard/Wachtell-affiliated XBMA; LSEG data, inflation-adjusted to 2025 $)', url='https://xbma.org/wp-content/uploads/2026/02/XBMA-Annual-Review-for-2025.pdf')
C['ma_2026'] = dict(ytd_lseg_tusd=3.9, h1_lseg_tusd=2.85, ytd_mergermarket_tusd=4.44, src='LSEG Deals Intelligence via Reuters/Investment Executive; Mergermarket 9M26 highlights', url='https://ionanalytics.com/insights/mergermarket/ma-highlights-9m26/')
save('ma_global_lseg_xbma.csv', pd.DataFrame(C['ma']).assign(unit='USD bn, 2025 dollars', source=C['ma_src']['source'], url=C['ma_src']['url']))

# ================================================================ 7. Stock market cap & listed companies (World Bank)
mc = wb('CM.MKT.LCAP.CD'); ld = wb('CM.MKT.LDOM.NO')
mcap = []
for y in range(1975, 2026):
    g = lambda df, i: df[(df.iso3 == i) & (df.year == y)].value
    w = g(mc, 'WLD')
    if not len(w): continue
    row = dict(year=y, world=float(w.iloc[0]))
    for i in ['USA', 'CHN', 'JPN', 'IND', 'GBR']:
        v = g(mc, i); row[i] = float(v.iloc[0]) if len(v) else None
    for i in ['WLD', 'USA', 'CHN', 'IND', 'JPN']:
        v = g(ld, i); row['n_' + i] = int(v.iloc[0]) if len(v) else None
    mcap.append(row)
C['mcap'] = mcap
C['mcap_src'] = dict(source='World Bank (WFE data): CM.MKT.LCAP.CD, CM.MKT.LDOM.NO', url=WB_URL.format('CM.MKT.LCAP.CD'))
C['wfe_2025'] = dict(mcap_tusd=151.94, added_tusd=23, src='WFE FY2025 market highlights press release (27 Feb 2026)', url='https://www.world-exchanges.org/news/articles/new-wfe-data-public-markets-post-strong-growth-2025-despite-geopolitical-instability')
save('stock_market_cap_listed_wb.csv', pd.DataFrame(mcap).assign(unit='current USD', source=C['mcap_src']['source'], url=C['mcap_src']['url']))

# ================================================================ 8. Trillion-dollar club (Wikipedia table, parsed from saved HTML)
tb = pd.read_html(os.path.join(RAW, 'wiki_market_cap_list.html'))[0]
tb.columns = ['company', 'country', 'peak_nominal', 'peak_real', 'peak_date', 't1', 't2', 't3', 't4', 't5', 'ref']
def dt(s):
    try: return pd.to_datetime(str(s), format='%d %b %Y').strftime('%Y-%m-%d')
    except Exception: return None
tri = []
for _, r in tb.iterrows():
    rec = dict(company=r.company, peak_busd=int(r.peak_nominal), peak_date=dt(r.peak_date), cite=str(r.ref))
    for k in ['t1', 't2', 't3', 't4', 't5']: rec[k] = dt(r[k])
    tri.append(rec)
for rec in tri:  # Aramco only listed on 11 Dec 2019; Wikipedia's 2018 $1T date refers to a pre-IPO valuation
    if rec['company'] == 'Saudi Aramco':
        rec['t1'] = '2019-12-11'; rec['note'] = 'Listed 11 Dec 2019 (debut value ~$1.88T); Wikipedia shows a 2018 pre-IPO $1T date.'
    if 'citation needed' in rec['cite']: rec['note'] = 'Wikipedia entry lacks a citation — verify before quoting.'
C['trillion'] = tri
C['trillion_src'] = dict(source='Wikipedia, "List of public corporations by market capitalization" — trillion-dollar companies table (retrieved 27 Oct 2026); first date each milestone was exceeded', url='https://en.wikipedia.org/wiki/List_of_public_corporations_by_market_capitalization')
save('trillion_dollar_club.csv', pd.DataFrame(tri).rename(columns={'t1': 'first_1T', 't2': 'first_2T', 't3': 'first_3T', 't4': 'first_4T', 't5': 'first_5T'}).assign(source=C['trillion_src']['source'], url=C['trillion_src']['url']))

# ================================================================ 9. Capital pools
GS = 'https://globalswf.com/ranking'
swf = [('NBIM (Norway GPFG)', 'SWF', 'Norway', 2284), ('SAFE Investment Co.', 'SWF', 'China', 2047), ('GPIF', 'Pension', 'Japan', 1962),
       ('CIC', 'SWF', 'China', 1567), ('National Pension Service', 'Pension', 'South Korea', 1210), ('GIC', 'SWF', 'Singapore', 1161),
       ('ADIA', 'SWF', 'UAE (Abu Dhabi)', 1128), ('FRTIB (US Thrift Savings Plan)', 'Pension', 'USA', 1085), ('KIA', 'SWF', 'Kuwait', 1002),
       ('PIF', 'SWF', 'Saudi Arabia', 906), ('APG', 'Pension', 'Netherlands', 641), ('CalPERS', 'Pension', 'USA', 635),
       ('CPP Investments', 'Pension', 'Canada', 608), ('QIA', 'SWF', 'Qatar', 580), ('CPF', 'Pension', 'Singapore', 504)]
C['swf'] = [dict(name=a, type=b, country=c, busd=d) for a, b, c, d in swf]
C['swf_src'] = dict(source='Global SWF ranking of sovereign wealth & public pension funds (last updated Oct 2026; central banks excluded)', url=GS)
save('sovereign_and_pension_funds_globalswf.csv', pd.DataFrame(C['swf']).assign(unit='USD bn', source=C['swf_src']['source'], url=GS))
gdp_w = gdp[gdp.iso3 == 'WLD'].sort_values('year').iloc[-1]
mc24 = [m for m in mcap if m['year'] == 2024][0]
C['pools'] = [
    dict(name='World stock market value (WFE, end-2025)', tusd=151.94, src=C['wfe_2025']['src'], url=C['wfe_2025']['url']),
    dict(name=f"World GDP ({int(gdp_w.year)})", tusd=round(gdp_w.value / 1e12, 1), src='World Bank NY.GDP.MKTP.CD', url=WB_URL.format('NY.GDP.MKTP.CD')),
    dict(name='US stock market value (World Bank, 2024)', tusd=round(mc24['USA'] / 1e12, 1), src='World Bank CM.MKT.LCAP.CD', url=WB_URL.format('CM.MKT.LCAP.CD')),
    dict(name='BlackRock assets under management (30 Sep 2026)', tusd=15.5, src='BlackRock Q3 2026 earnings supplement (SEC 8-K exhibit 99.2)', url='https://www.sec.gov/Archives/edgar/data/0002012383/000119312526420979/blk-ex99_2.htm'),
    dict(name='Top 300 co-operatives, turnover (2023)', tusd=2.79, src='World Cooperative Monitor 2025', url='https://monitor.coop/sites/default/files/2025-10/wcm_executive_summary_2025_en.pdf'),
    dict(name='Norway oil fund NBIM (Oct 2026)', tusd=2.28, src='Global SWF', url=GS),
    dict(name='Global FDI flows (2025, UNCTAD)', tusd=1.6, src='UNCTAD World Investment Report 2026', url='https://investmentpolicy.unctad.org/publications/1324/world-investment-report-2026-international-investment-in-a-turbulent-era'),
    dict(name='Global venture capital invested (2025, KPMG/PitchBook)', tusd=round(vc[-1]['global_'] / 1000, 2), src=C['vc_src']['source'], url=C['vc_src']['url']),
    dict(name='Global IPO proceeds (2025, EY)', tusd=0.187, src='EY Global IPO Trends Q3 2026', url=EY26),
]
save('capital_pools_compared.csv', pd.DataFrame(C['pools']).assign(unit='USD trillion'))

# ================================================================ 10. Co-operatives (World Cooperative Monitor 2025, FY2023 data)
WCM = 'https://monitor.coop/sites/default/files/2025-10/wcm_executive_summary_2025_en.pdf'
C['coop_turnover'] = [dict(rank=i + 1, name=n, country=c, busd=v) for i, (n, c, v) in enumerate([
    ('Groupe Crédit Agricole', 'France', 107.42), ('State Farm', 'USA', 93.79), ('REWE Group', 'Germany', 90.81), ('Groupe BPCE', 'France', 82.83),
    ('Groupe Crédit Mutuel', 'France', 69.15), ('ACDLEC – E.Leclerc', 'France', 66.82), ('Cooperative Financial Network', 'Germany', 58.08),
    ('Edeka Zentrale', 'Germany', 54.47), ('Nonghyup', 'South Korea', 51.23), ('Nationwide', 'USA', 49.68)])]
C['coop_gdppc'] = [dict(rank=i + 1, name=n, country=c, ratio=v) for i, (n, c, v) in enumerate([
    ('Gujarat Co-op Milk Marketing Federation (Amul)', 'India', 2899260), ('IFFCO', 'India', 2555994), ('Groupe Crédit Agricole', 'France', 2403513),
    ('Sistema Unimed', 'Brazil', 1898376), ('Groupe BPCE', 'France', 1853431), ('REWE Group', 'Germany', 1671047),
    ('Groupe Crédit Mutuel', 'France', 1547252), ('Nonghyup', 'South Korea', 1546631), ('ACDLEC – E.Leclerc', 'France', 1495210), ('Nippon Life', 'Japan', 1144312)])]
C['coop_top300_trend'] = [dict(year=2017, busd=1909.69), dict(year=2019, busd=2052.63), dict(year=2021, busd=2213.21), dict(year=2023, busd=2786.99)]
C['coop_src'] = dict(source='ICA–Euricse World Cooperative Monitor 2025 executive summary (FY2023 data)', url=WCM)
C['coop_facts'] = dict(n_coops='3 million', members='1 billion+ (12%+ of humanity)', jobs='280 million (10% of employed population)',
                       src='International Cooperative Alliance, Facts and figures', url='https://ica.coop/en/cooperatives/facts-and-figures',
                       amul_fy26_crore=73450, amul_fy25_crore=65911, amul_brand='₹1 lakh crore+ (~$12B) brand turnover FY26', amul_farmers='36 lakh',
                       amul_src='GCMMF FY2025-26 results as reported by AgroSpectrum India (Apr 2026)', amul_url='https://agrospectrumindia.com/2026/04/10/amuls-turnover-tops-rs-1-lakh-crore-driven-by-scale-and-farmer-network.html')
save('coops_top10_turnover_wcm.csv', pd.DataFrame(C['coop_turnover']).assign(unit='USD bn (2023)', source=C['coop_src']['source'], url=WCM))
save('coops_top10_turnover_over_gdppc_wcm.csv', pd.DataFrame(C['coop_gdppc']).assign(unit='turnover / GDP per capita', source=C['coop_src']['source'], url=WCM))

# ================================================================ 11. FDI & trade
fdi = wb('BX.KLT.DINV.CD.WD'); tr = wb('NE.TRD.GNFS.ZS')
C['fdi'] = [dict(year=y, world=series(fdi, 'WLD').get(y), india=series(fdi, 'IND').get(y), china=series(fdi, 'CHN').get(y), usa=series(fdi, 'USA').get(y)) for y in range(1990, 2026)]
C['trade'] = {iso: series(tr, iso, 1975, 2024) for iso in ['WLD', 'IND', 'CHN', 'USA', 'DEU', 'GBR', 'JPN', 'BRA']}
C['fdi_src'] = dict(source='World Bank BX.KLT.DINV.CD.WD (IMF BoP data); trade = NE.TRD.GNFS.ZS', url=WB_URL.format('BX.KLT.DINV.CD.WD'))
C['unctad'] = dict(global_fdi_2025_tusd=1.6, growth='+6%', india_2025_busd=38.89, india_2024_busd=27.09, india_rank=11,
                   src='UNCTAD World Investment Report 2026 (7 Jul 2026), via IISD/press coverage',
                   url='https://www.iisd.org/itn/2026/09/09/world-investment-report-2026-fdi-recovers-to-usd-1-6-trillion-but-concentration-deepens/')
save('fdi_net_inflows_wb.csv', pd.DataFrame(C['fdi']).assign(unit='current USD', source='World Bank BX.KLT.DINV.CD.WD', url=WB_URL.format('BX.KLT.DINV.CD.WD')))
save('trade_pct_gdp_wb.csv', tr[tr.iso3.isin(C['trade'])].assign(source='World Bank NE.TRD.GNFS.ZS', url=WB_URL.format('NE.TRD.GNFS.ZS')))

# ---------------------------------------------------------------- key numbers for tiles/notes (computed)
ind_inf = next((r for r in C['informal_country'] if r['iso3'] == 'IND'), None)
ind_nb = C['newbiz'].get('IND', {})
C['key'] = dict(
    world_informal=inf_income[0]['pct'], india_informal=ind_inf['pct'] if ind_inf else None, india_informal_year=ind_inf['year'] if ind_inf else None,
    india_newbiz_density=ind_nb.get(max(ind_nb)) if ind_nb else None, india_newbiz_year=max(ind_nb) if ind_nb else None,
    india_newbiz_regs=C['newbiz_reg'].get('IND', {}).get(max(ind_nb)) if ind_nb else None,
    uk_newbiz_density=C['newbiz'].get('GBR', {}).get(2024), world_newbiz_density=C['newbiz'].get('WLD', {}).get(2024),
    us_mcap_share_2024=round(100 * mc24['USA'] / mc24['world'], 1), world_mcap_2024_tusd=round(mc24['world'] / 1e12, 1),
    listed_2024=mc24['n_WLD'], vc_2025=vc[-1]['global_'], vc_2021=vc[2]['global_'], india_vc_2025=vc[-1]['india'], india_vc_2021=vc[2]['india'],
    world_selfemp=C['selfemp']['WLD'].get(2025), india_selfemp=C['selfemp']['IND'].get(2025),
)
C['generated'] = datetime.date.today().isoformat()

js = 'window.ATLAS = window.ATLAS || {};\nwindow.ATLAS.context = ' + json.dumps(C, ensure_ascii=False, separators=(',', ':'), allow_nan=False, default=str) + ';\n'
os.makedirs(os.path.join(SITE, 'data'), exist_ok=True)
open(os.path.join(SITE, 'data', 'context.js'), 'w', encoding='utf-8').write(js)
print('context.js', round(len(js.encode()) / 1e6, 2), 'MB')
print(json.dumps(C['key'], indent=1))
print('VC', vc)
