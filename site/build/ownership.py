"""Build site/data/ownership.js  ->  window.ATLAS.ownership

Two lenses on "who owns the world's business":
  A. Fortune Global 500 (2025) — one consistent list of the 500 largest companies by revenue, ranked as
     PARENT groups (Sinopec Group, not Sinopec Corp). Every row re-labelled here into six ownership types.
  B. Forbes Global 2000 (2025) — listed companies only, with a curated flag for state control
     (majority/controlling, or a significant 20-50% state stake). Lets us show India's PSUs, China's listed SOEs.
Plus curated 'invisible giants' not on any list, Forbes' largest US private companies, and a curated
family / foundation control table. All curated labels are from public knowledge (2025) — verify before quoting.
"""
import json, os, re, unicodedata
import pandas as pd
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
D = os.path.join(ROOT, 'data')
OUT = os.path.join(ROOT, 'site', 'data', 'ownership.js')

g = pd.read_csv(os.path.join(D, 'global2000_2026.csv'), encoding='utf-8-sig')
f = pd.read_csv(os.path.join(D, 'fortune_g500_2026.csv'), encoding='utf-8-sig')
lab = pd.read_csv(os.path.join(D, 'fortune_labels.csv'), encoding='utf-8-sig')
pv = pd.read_csv(os.path.join(D, 'private_us_2025.csv'), encoding='utf-8-sig')
mt = pd.read_csv(os.path.join(ROOT, 'data_analysis', 'output', 'data', 'ownership__margin_tests.csv'))


def fix(s):
    """Repair the odd mojibake (� for accented chars) in source names."""
    if not isinstance(s, str):
        return s
    return s.replace('�', 'e').strip()


g['company'] = g['company'].map(fix)
f['company'] = f['company'].map(fix)
f['headquarters'] = f['headquarters'].map(fix)

# ------------------------------------------------------------------------------------------
# B. Forbes Global 2000: curated state-control flags.  M = state is majority / controlling owner;
#    S = significant state minority stake (roughly 20-50%, state usually largest holder).
# ------------------------------------------------------------------------------------------
STATE_M = {
 # India — central PSUs / PSU banks / PSU insurers
 'Life Insurance Corp. of India', 'Indian Oil', 'Oil & Natural Gas', 'State Bank of India', 'Bharat Petroleum', 'NTPC',
 'Bank of Baroda', 'Canara Bank', 'Coal India', 'GAIL India', 'Punjab National Bank', 'Union Bank of India', 'Power Finance',
 'Bank of India', 'Indian Bank', 'General Insurance Corporation Of India', 'Power Grid of India', 'Central Bank of India',
 'IDBI Bank', 'Bank of Maharashtra', 'Indian Railway Finance', 'Bharat Electronics',
 # China (labelled for all firms with revenue >= ~$10B)
 'Sinopec', 'PetroChina', 'China State Construction Engineering', 'ICBC', 'Agricultural Bank of China', 'China Construction Bank',
 'Bank of China', 'China Railway Group', 'China Railway Construction', 'China Communications Construction', 'Xiamen C&D', 'SAIC Motor',
 'Power Construction Corporation of China', 'Postal Savings Bank Of China (PSBC)', 'Sinopharm Group', 'PICC', 'Wuchan Zhongda Group',
 'Metallurgical Corp of China', 'China Telecom', 'Jiangxi Copper', 'China Energy Engineering', 'China Life Insurance', 'China Citic Bank',
 'Xiamen Xiangyu', 'Xiamen International Trade Group', 'Poly Developments & Holdings Group', 'China Shenhua Energy',
 'Baoshan Iron & Steel', 'Shanghai Construction', 'Shanghai Pharmaceuticals', 'China Everbright Bank', 'CRRC',
 'Huaneng Power International', 'Aluminum Corp of China', 'Cosco Shipping', 'Zheshang Development Group', 'BAIC Motor',
 'China Coal Energy', 'Yunnan Copper', 'China National Building', 'China National Chemical', 'Shaanxi Coal Industry',
 'China Merchants Shekou Industrial Zone Holdings', 'GD Power Development', 'Shaanxi Construction Engineering Group',
 'Chongqing Changan Auto', 'China Communications Services', 'Kweichow Moutai', 'Tongling Nonferrous Metals', 'Hunan Valin Steel',
 'China Southern Airlines', 'China Eastern Airlines', 'Yankuang Energy Group', 'HBIS', 'Datang International Power', 'Sumec Corporation',
 'Shanghai Electric Group', 'China Reinsurance Group', 'Huadian Power International', 'China Nuclear Engineering Corporation', 'BBMG',
 'Guangzhou Automobile Group', 'Sichuan Road & Bridge', 'Dongfeng Motor Group', 'Sinotrans Ltd.', 'Beijing Shougang', 'China Tower Corp.',
 'Anhui Construction Engineering Group', 'Sinotruk Hong Kong', 'Zhejiang Zheneng Electric Power', 'XCMG Construction Machinery',
 'CGN Power', 'AviChina Industry & Technology', 'Tianshan Material', 'China Yangtze Power', 'Shandong Gold Mining', 'China CSSC Holdings',
 'Wuliangye Yibin', 'Daqin Railway', 'China National Nuclear Power', 'Shandong Hi-Speed Road & Bridge Group', 'Shanghai Tunnel Engineering',
 # Hong Kong-listed mainland SOEs and HK public bodies
 'China Mobile', 'CITIC', 'CNOOC', 'China Unicom', 'China Resources Land', 'China Resources Pharmaceutical Group', 'China Taiping Insurance',
 'China Resources Power', 'China Resources Gas Group', 'Yuexiu Property', 'Beijing Enterprises', 'MTR', 'China Power International Development',
 'China Resources Beer (Holdings)', 'China Merchants Port Holdings',
 # Gulf
 'Saudi Arabian Oil Company (Saudi Aramco)', 'Saudi Electricity', 'Saudi Telecom', 'Saudi Arabian Mining', 'ELM',
 'Emirates NBD', 'Etisalat', 'TAQA', 'Abu Dhabi Commercial Bank', 'Borouge', 'Qatar National Bank', 'Ooredoo Q.P.S.C', 'Industries Qatar',
 'Arab Banking',
 # Rest of Asia
 'Bank Rakyat Indonesia (BRI)', 'Bank Mandiri', 'Telkom Indonesia', 'Bank Negara Indonesia', 'PTT ', 'Krung Thai Bank', 'Airports of Thailand',
 'SingTel', 'Singapore Airlines', 'ST Engineering', 'China Aviation Oil', 'Olam Group', 'Korea Electric Power', 'Korea Gas',
 'Industrial Bank of Korea', 'HMM', 'Tokyo Electric Power', 'Taiwan Cooperative Financial',
 'Commercial Bank For Investment & Development Of Vietnam', 'Vietin Bank', 'Joint Stock Commercial Bank for Foreign Trade of Vietnam',
 # Europe
 'Equinor', 'Telenor', 'Kongsberg Gruppen ', 'PGE Polska Grupa Energetyczna', 'Poste Italiane', 'A2A', 'Aeroports de Paris',
 'EnBW Energie Baden-Wurttemberg', 'Swisscom', 'Schweizerische Nationalbank', 'Banque Cantonale Vaudoise', 'Basler Kantonalbank',
 'Luzerner Kantonalbank', 'St. Galler Kantonalbank', 'BEKB-BCBE', 'Orsted', 'Aena', 'Fortum', 'Verbund', 'CEZ Group',
 'VakifBank', 'Halkbank',
 # Americas
 'Petrobras', 'Banco do Brasil', 'Companhia Energetica de Minas Gerais', 'Ecopetrol', 'YPF ', 'Fannie Mae', 'Freddie Mac',
}
STATE_S = {
 'LIC Housing Finance',
 'Bank of Communications', 'China Merchants Bank', 'Industrial Bank ', 'China Pacific Insurance', 'Shanghai Pudong Development',
 'China Vanke', 'Zijin Mining Group', 'Greenland Holdings Group', 'Weichai Power', 'BOE Technology Group', 'Huaxia Bank',
 'Wanhua Chemical Group', 'Greentown China Holdings', 'Bank Of Jiangsu', 'Legend Holding', 'Bank of Beijing', 'China Zheshang Bank',
 'ZTE', 'Bank of Ningbo', 'IEIT Systems', 'Citic Securities', 'Bank Of Shanghai', 'Bank of Nanjing', 'Hikvision', 'New China Life Insurance',
 'China Jinmao', 'China Mengniu Dairy', 'Far East Horizon',
 'The Saudi National Bank', 'Riyad Bank', 'ACWA Power', 'First Abu Dhabi Bank', 'Emaar Properties', 'Dubai Islamic Bank',
 'Commercial Bank Dubai', 'National Bank of Ras Al-Khaimah (P.S.C.)', 'Commercial Bank of Qatar ', 'Kuwait Finance House',
 'Sime Darby', 'Tenaga Nasional', 'Maybank', 'CIMB Group Holdings', 'RHB Bank', 'PTT Global Chemical', 'Bangchak', 'DBS', 'Keppel Ltd',
 'Japan Post Holdings', 'Nippon Telegraph & Tel', 'Japan Tobacco', 'Inpex',
 'Chunghwa Telecom', 'China Steel', 'Mega Financial Holding', 'First Financial Holding', 'Hua Nan Financial', 'Chang Hwa Bank',
 'Taiwan Business Bank',
 'DNB Bank', 'Norsk Hydro', 'Yara International', 'ORLEN Spolka Akcyjna', 'Grupa PZU', 'PKO Bank Polski', 'KGHM Polska Miedz',
 'Bank Pekao', 'Alior Bank', 'Eni', 'Enel', 'Leonardo', 'Saipem', 'Hera', 'Terna', 'Snam', 'ENGIE', 'Orange', 'Air France-KLM', 'Thales',
 'AIRBUS', 'Deutsche Telekom', 'Volkswagen Group', 'Elia System Operator', 'Telia', 'Neste', 'OMV Group', 'Public Power',
 'Turkish Airlines', 'Eletrobras', 'Hydro One',
}
# Eletrobras appears with mojibake in the source; match loosely below.
g['state'] = 'No'
for name in STATE_M:
    hit = g['company'] == fix(name)
    if not hit.any():
        hit = g['company'].str.strip() == name.strip()
    if not hit.any():
        print('WARN state-M name not found:', name)
    g.loc[hit, 'state'] = 'Majority / control'
for name in STATE_S:
    hit = (g['company'] == fix(name)) | (g['company'].str.strip() == name.strip())
    if name == 'Eletrobras':
        hit = g['company'].str.startswith('Eletrobr')
    if not hit.any():
        print('WARN state-S name not found:', name)
    g.loc[hit, 'state'] = 'Significant stake'
# China: only firms >= $10B revenue were assessed
g['assessed'] = True
g.loc[(g.country == 'China') & (g.revenue_musd < 10000), 'assessed'] = False

g['margin'] = np.where(g.revenue_musd > 0, g.profits_musd / g.revenue_musd * 100, np.nan)

# country-level state share (Forbes listed lens)
rows = []
for c, d in g.groupby('country'):
    tot = d.revenue_musd.sum()
    if tot < 60000 and c not in ('Norway', 'Qatar', 'Indonesia', 'Malaysia', 'Vietnam', 'Czech Republic', 'Colombia'):
        continue
    m = d[d.state == 'Majority / control'].revenue_musd.sum()
    s = d[d.state == 'Significant stake'].revenue_musd.sum()
    rows.append(dict(country=c, firms=len(d), rev=round(tot), rev_m=round(m), rev_s=round(s),
                     n_m=int((d.state == 'Majority / control').sum()), n_s=int((d.state == 'Significant stake').sum()),
                     pct_m=round(m / tot * 100, 1), pct_s=round(s / tot * 100, 1),
                     mv_pct_m=round(d[d.state == 'Majority / control'].market_value_musd.sum() / d.market_value_musd.sum() * 100, 1),
                     unassessed_pct=round(d[~d.assessed].revenue_musd.sum() / tot * 100, 1)))
state_by_country = sorted(rows, key=lambda r: -(r['pct_m'] + r['pct_s']))

# India deep dive
ind = g[g.country == 'India'].sort_values('revenue_musd', ascending=False)
india = [dict(company=r.company, rev=r.revenue_musd, profit=r.profits_musd, mv=r.market_value_musd, emp=r.employees,
              margin=None if pd.isna(r.margin) else round(r.margin, 1), sector=r.sector, industry=r.industry_canon,
              psu=r.state != 'No', state=r.state) for r in ind.itertuples()]
def grp_stats(d):
    d = d[d.revenue_musd > 0]
    return dict(n=len(d), rev=round(d.revenue_musd.sum()), profit=round(d.profits_musd.sum()), mv=round(d.market_value_musd.sum()),
                emp=int(d.employees.fillna(0).sum()),
                agg_margin=round(d.profits_musd.sum() / d.revenue_musd.sum() * 100, 1),
                med_margin=round(float(d.margin.median()), 1),
                mv_to_rev=round(d.market_value_musd.sum() / d.revenue_musd.sum(), 2),
                mv_to_profit=round(d.market_value_musd.sum() / max(d.profits_musd.sum(), 1), 1))
india_stats = {'PSU (state-controlled)': grp_stats(ind[ind.state != 'No']), 'Private sector': grp_stats(ind[ind.state == 'No'])}
china = g[g.country == 'China']
china_stats = {'State-controlled': grp_stats(china[china.state != 'No'] if True else china),
               'Private / no state control': grp_stats(china[(china.state == 'No') & china.assessed])}

# Forbes listed lens: margins
def mlabel(r):
    return {'Majority / control': 'Listed, state-controlled', 'Significant stake': 'Listed, significant state stake'}.get(r, 'Listed, no major state stake')
g['olabel'] = g['state'].map(mlabel)
forbes_margin = []
for k, d in g[g.assessed & (g.revenue_musd > 0)].groupby('olabel'):
    st = grp_stats(d)
    st['label'] = k
    forbes_margin.append(st)

# ------------------------------------------------------------------------------------------
# A. Fortune Global 500 — relabel every row.
# ------------------------------------------------------------------------------------------
lab = lab.set_index('slug')
F_STATE_UNLISTED = {  # Fortune 'Private' rows that are really state-owned parent groups (and other unlisted SOEs)
 'sinopec-group', 'china-state-construction-engineering', 'china-life-insurance', 'china-railway-engineering',
 'china-mobile-communications', 'china-railway-construction', 'citic-group', 'china-communications-construction', 'china-resources-national',
 'china-national-offshore-oil', 'china-southern-power-grid', 'china-minmetals', 'xiamen-cd', 'sinopharm', 'china-telecommunications',
 'jiangxi-copper', 'aluminum-corp-of-china', 'china-energy-engineering-group', 'china-cosco-shipping', 'hbis-group', 'guangzhou-automobile-industry-group',
 'dongfeng-motor', 'datong-coal-mine-group', 'shandong-hi-speed-group', 'china-national-building-material-group', 'crrc-group',
 'beijing-automotive-group', 'shandong-gold-group', 'tongling-nonferrous-metals-group', 'deutsche-bahn', 'emirates-group',
 'xiamen-xiangyu-group',
}
F_PRIVATE = {'hengli-group', 'zhejiang-rongsheng-holding-group', 'shandong-weiqiao-pioneering-group', 'shenghong-holding-group',
             'pacific-construction-group', 'publix-super-markets', 'tsingshan-holding-group', 'jingye-group', 'heraeus-holding',
             'ingka-group', 'jiangsu-shagang-group', 'new-hope-holding-group', 'beijing-jianlong-heavy-industry-group'}
F_MUTUAL = {'rewe-group', 'groupe-bpce', 'coop-group', 'sumitomo-life-insurance', 'dz-bank'}
F_LISTED_OTHER = {'discovery', 'x5-retail-group', 'magnit', 'christian-dior', 'energy-transfer-equity', 'plains-gp-holdings'}
F_LISTED_STATE = {'sberbank', 'vtb-bank', 'gazprom', 'qnb-group', 'uniper', 'rosneft-oil',
                  'industrial-commercial-bank-of-china', 'agricultural-bank-of-china', 'china-construction-bank', 'bank-of-china',
                  'fannie-mae', 'freddie-mac', 'saic-motor', 'life-insurance-corp-of-india', 'equinor', 'indian-oil', 'petrobras', 'ptt',
                  'state-bank-of-india', 'wuchan-zhongda-group', 'oil-natural-gas', 'korea-electric-power', 'banco-do-brasil',
                  'bharat-petroleum', 'shanghai-pharmaceuticals-holding', 'tokyo-electric-power', 'saudi-aramco', 'peoples-insurance-co-of-china'}
F_LISTED_SIG = {'bank-of-communications', 'china-merchants-bank', 'china-pacific-insurance-group', 'industrial-bank', 'zijin-mining-group',
                'shanghai-pudong-development-bank', 'new-china-life-insurance', 'japan-post-holdings', 'nippon-telegraph-telephone', 'orlen',
                'eni-2', 'enel', 'engie', 'orange', 'deutsche-telekom', 'air-france-klm-group', 'omv-group', 'airbus-group', 'volkswagen'}

def f_owner(r):
    s = r.slug
    if s in F_LISTED_STATE: return 'Listed, state-controlled'
    if s in F_LISTED_SIG: return 'Listed, significant state stake'
    if s in F_STATE_UNLISTED: return 'State-owned, unlisted'
    if s in F_PRIVATE: return 'Private (family / founder / foundation)'
    if s in F_MUTUAL: return 'Mutual / co-operative'
    if s in F_LISTED_OTHER: return 'Listed, no major state stake'
    if s in lab.index:
        o = lab.loc[s, 'ownership']
        return {'State-owned': 'State-owned, unlisted', 'Private': 'Private (family / founder / foundation)',
                'Mutual / Cooperative': 'Mutual / co-operative', 'Public (outside Forbes)': 'Listed, no major state stake',
                'DUPLICATE': 'Listed, no major state stake'}[o]
    if r.company_type == 'Private':
        print('WARN unlabelled Fortune private:', s, r.company)
        return 'Private (family / founder / foundation)'
    return 'Listed, no major state stake'

missing = (F_STATE_UNLISTED | F_PRIVATE | F_MUTUAL | F_LISTED_OTHER | F_LISTED_STATE | F_LISTED_SIG) - set(f.slug)
if missing: print('WARN slugs not in Fortune file:', missing)
f['owner'] = f.apply(f_owner, axis=1)

US_ST = r', (Ala|Ariz|Ark|Calif|Colo|Conn|Del|Fla|Ga|Ill|Ind|Iowa|Kan|Ky|La|Md|Mass|Mich|Minn|Miss|Mo|Neb|Nev|N\.H|N\.J|N\.Y|N\.C|Ohio|Okla|Ore|Pa|R\.I|S\.C|Tenn|Texas|Tex|Utah|Va|Wash|Wis)\.?$'
CITY = {
 'Seattle': 'United States', 'Omaha': 'United States', 'NewYork City': 'United States', 'New York City': 'United States', 'U.S.': 'United States',
 'Indianapolis': 'United States', 'St. Louis': 'United States', 'Charlotte': 'United States', 'Houston': 'United States', 'Detroit': 'United States',
 'Atlanta': 'United States', 'Washington, D.C.': 'United States', 'Cincinnati': 'United States', 'San Francisco': 'United States', 'Dallas': 'United States',
 'San Antonio': 'United States', 'Minneapolis': 'United States', 'Austin': 'United States', 'Boise': 'United States', 'Chicago': 'United States',
 'Nashville': 'United States', 'Palo Alto': 'United States', 'Santa Clara': 'United States', 'Memphis': 'United States', 'Louisville': 'United States',
 'Philadelphia': 'United States', 'Boston': 'United States', 'Milwaukee': 'United States', 'Fort Worth': 'United States', 'Miami': 'United States',
 'Pittsburgh': 'United States', 'San Diego': 'United States', 'San Jose': 'United States', 'Tulsa': 'United States', 'Spring, Texas': 'United States',
 'Arlington, Texas': 'United States', 'Round Rock, Texas': 'United States',
 'Beijing': 'China', 'Shanghai': 'China', 'Shenzhen': 'China', 'Hong Kong': 'Hong Kong',
 'Tokyo': 'Japan', 'Osaka': 'Japan', 'Toyota': 'Japan',
 'Seoul': 'South Korea', 'South Korea': 'South Korea',
 'London': 'United Kingdom', 'U.K.': 'United Kingdom', 'Edinburgh': 'United Kingdom', 'Cambridge': 'United Kingdom', 'Chertsey': 'United Kingdom',
 'Cirencester': 'United Kingdom', 'Newbury': 'United Kingdom', 'Welwyn Garden City': 'United Kingdom', 'Harmondsworth': 'United Kingdom', 'Woking, Surrey': 'United Kingdom',
 'Paris': 'France', 'Courbevoie': 'France', 'Massy': 'France', 'Nanterre': 'France', 'Montrouge': 'France', 'Boulogne-Billancourt': 'France',
 'Aubervilliers': 'France', 'Clichy': 'France', 'Issy-les-Moulineaux': 'France', 'Rueil-Malmaison': 'France', 'St. Denis': 'France',
 'Wolfsburg': 'Germany', 'Munich': 'Germany', 'Stuttgart': 'Germany', 'Bonn': 'Germany', 'Germany': 'Germany', 'Essen': 'Germany', 'Frankfurt': 'Germany',
 'Ludwigshafen': 'Germany', 'Cologne': 'Germany', 'Hanover': 'Germany', 'Leverkusen': 'Germany', 'Hanau': 'Germany', 'Walldorf': 'Germany', 'Berlin': 'Germany',
 'Leinfelden-Echterdingen': 'Germany', 'Hamburg': 'Germany', 'Friedrichshafen': 'Germany', 'Karlsruhe': 'Germany', 'Gerlingen-Schillerhohe': 'Germany',
 'Gerlingen-Schillerhehe': 'Germany', 'Gerlingen-Schillerhöhe': 'Germany', 'Düsseldorf': 'Germany', 'Desseldorf': 'Germany',
 'Baar': 'Switzerland', 'Vevey': 'Switzerland', 'Zurich': 'Switzerland', 'Basel': 'Switzerland', 'Geneva': 'Switzerland',
 'Hoofddorp': 'Netherlands', 'Zaandam': 'Netherlands', 'Amstelveen': 'Netherlands', 'Leiden': 'Netherlands', 'Amsterdam': 'Netherlands',
 'Veldhoven': 'Netherlands', 'Rotterdam': 'Netherlands', 'Utrecht': 'Netherlands',
 'Madrid': 'Spain', 'Bilbao': 'Spain', 'A Coruña': 'Spain', 'A Coruea': 'Spain', 'Valencia': 'Spain',
 'Rome': 'Italy', 'Trieste': 'Italy', 'Turin': 'Italy', 'Milan': 'Italy',
 'Mumbai': 'India', 'New Delhi': 'India',
 'Toronto': 'Canada', 'Calgary': 'Canada', 'Montreal': 'Canada',
 'Stavanger': 'Norway', 'Bangkok': 'Thailand', 'Moscow': 'Russia', 'St. Petersburg': 'Russia', 'Krasnodar': 'Russia',
 'Rio de Janeiro': 'Brazil', 'Sao Paulo': 'Brazil', 'Singapore': 'Singapore', 'Istanbul': 'Turkey', 'Ireland': 'Ireland', 'Dublin': 'Ireland',
 'Plock': 'Poland', 'Luxembourg': 'Luxembourg', 'Leuven': 'Belgium', 'Copenhagen': 'Denmark', 'Hedehusene': 'Denmark',
 'Melbourne': 'Australia', 'Sydney': 'Australia', 'Mexico City': 'Mexico', 'Gothenburg': 'Sweden', 'Vienna': 'Austria', 'Lisbon': 'Portugal',
 'Dubai': 'United Arab Emirates', 'Doha': 'Qatar', 'Jakarta': 'Indonesia', 'Kuala Lumpur': 'Malaysia', 'Prague': 'Czech Republic',
}
def hq_country(h):
    if h in CITY: return CITY[h]
    if re.search(US_ST, h): return 'United States'
    for k in ['China', 'Japan', 'Taiwan', 'South Korea', 'India', 'Brazil', 'Australia', 'France', 'Netherlands', 'Denmark', 'Switzerland',
              'Saudi Arabia', 'Mexico']:
        if h.endswith(k): return k
    if h.endswith('Ontario') or h.endswith('Quebec'): return 'Canada'
    print('WARN no country for HQ', h)
    return 'Other'
f['country'] = f['headquarters'].map(hq_country)
f['margin'] = np.where(f.revenues_musd > 0, f.profits_musd / f.revenues_musd * 100, np.nan)

OWN_ORDER = ['Listed, no major state stake', 'Listed, significant state stake', 'Listed, state-controlled', 'State-owned, unlisted',
             'Private (family / founder / foundation)', 'Mutual / co-operative']

def mix(d):
    out = []
    for o in OWN_ORDER:
        x = d[d.owner == o]
        out.append(dict(owner=o, n=len(x), rev=round(x.revenues_musd.sum()), profit=round(x.profits_musd.sum()),
                        agg_margin=round(x.profits_musd.sum() / x.revenues_musd.sum() * 100, 1) if len(x) else None,
                        med_margin=round(float(x.margin.median()), 1) if len(x) else None,
                        loss_makers=int((x.profits_musd < 0).sum())))
    return out
fortune_mix = mix(f)
fortune_tot = dict(n=len(f), rev=round(f.revenues_musd.sum()), profit=round(f.profits_musd.sum()))

top_c = f.country.value_counts().head(16).index.tolist()
fortune_country = []
for c in top_c:
    d = f[f.country == c]
    fortune_country.append(dict(country=c, n=len(d), rev=round(d.revenues_musd.sum()),
                                by={o: dict(n=int((d.owner == o).sum()), rev=round(d[d.owner == o].revenues_musd.sum())) for o in OWN_ORDER}))

fortune_rows = [dict(rank=int(r.rank), company=r.company, country=r.country, owner=r.owner, rev=r.revenues_musd, profit=r.profits_musd,
                     margin=None if pd.isna(r.margin) else round(r.margin, 1), hq=r.headquarters) for r in f.itertuples()]

# ------------------------------------------------------------------------------------------
# Invisible giants: big companies with no stock-market listing of the whole group
# ------------------------------------------------------------------------------------------
inv = []
for r in f[f.owner.isin(['State-owned, unlisted', 'Private (family / founder / foundation)', 'Mutual / co-operative'])].itertuples():
    inv.append(dict(company=r.company, country=r.country, owner=r.owner, rev=r.revenues_musd, profit=r.profits_musd,
                    src='Fortune Global 500 (2025)', note=''))
fortune_names = {re.sub(r'[^a-z]', '', x.lower())[:8] for x in f.company}
pv['company'] = pv['company'].str.strip()
for r in pv.head(40).itertuples():
    key = re.sub(r'[^a-z]', '', r.company.lower())[:8]
    if key in fortune_names:
        continue
    inv.append(dict(company=r.company, country='United States', owner='Private (family / founder / foundation)', rev=r.revenue_musd,
                    profit=None, src="Forbes America's Largest Private Companies (2025)", note=r.industry))
# Curated: giants absent from every list in this pack (revenue from company disclosures / press; approximate)
CURATED = [
 ('Vitol', 'Switzerland', 'Private (family / founder / foundation)', 331000, 'Employee-owned oil trader; 2024 revenue $331B (2023: $400B). Publishes little.'),
 ('Schwarz Group (Lidl, Kaufland)', 'Germany', 'Private (family / founder / foundation)', 181000, 'Owned by Dieter Schwarz Stiftung; FY2024 ~EUR 167B.'),
 ('ByteDance (TikTok, Douyin)', 'China', 'Private (family / founder / foundation)', 155000, 'VC/founder-owned; 2024 revenue ~$155B as reported by press, unaudited.'),
 ('Aldi (Sud + Nord)', 'Germany', 'Private (family / founder / foundation)', 121000, 'Albrecht family foundations; combined revenue estimate.'),
 ('Deloitte', 'United Kingdom', 'Private (family / founder / foundation)', 67200, 'Partnership network; FY2024 aggregate revenue $67.2B.'),
 ('Ineos', 'United Kingdom', 'Private (family / founder / foundation)', 65000, 'Jim Ratcliffe and partners; approximate.'),
 ('CMA CGM', 'France', 'Private (family / founder / foundation)', 55500, 'Saade family; 2024 revenue $55.5B.'),
 ('PwC', 'United Kingdom', 'Private (family / founder / foundation)', 55400, 'Partnership network; FY2024 $55.4B.'),
 ('EY', 'United Kingdom', 'Private (family / founder / foundation)', 51200, 'Partnership network; FY2024 $51.2B.'),
 ('KPMG', 'Netherlands', 'Private (family / founder / foundation)', 38400, 'Partnership network; FY2024 $38.4B.'),
]
for c in CURATED:
    inv.append(dict(company=c[0], country=c[1], owner=c[2], rev=c[3], profit=None, src='Curated (public disclosures / press, approximate)', note=c[4]))
NOTES = {
 'State Grid': 'Chinese central SOE (SASAC). Single largest electricity grid on earth; ~1.4M staff by its own reports.',
 'China National Petroleum': "PetroChina's unlisted parent (owns ~80%+ of it) — its revenue overlaps PetroChina's.",
 'Sinopec Group': 'Unlisted parent of listed Sinopec Corp.',
 'Trafigura Group': 'Employee-owned commodity trader, Singapore/Geneva.',
 'Bosch Group': 'Robert Bosch Stiftung (foundation) holds ~94% of equity; family/trust holds votes.',
 'Huawei Investment & Holding': 'Owned by its employee union (ESOP) + founder Ren Zhengfei (~1%).',
 'Ingka Holding (IKEA)': 'Owned by Stichting INGKA Foundation (Netherlands).',
 'Deutsche Bahn': 'Owned 100% by the German federal government.',
 'U.S. Postal Service': 'Independent agency of the US federal government.',
 'State Farm Insurance': 'Owned by its policyholders (mutual).',
 'Cargill': 'Cargill-MacMillan family ~88%; one of the largest private firms in the world.',
 'Koch': 'Koch family.', 'Mars': 'Mars family, ~100%.',
 'Publix Super Markets': 'Employee-owned (ESOP) — not listed though it files with the SEC.',
 'China Mobile Communications': 'Unlisted parent of listed China Mobile.',
 'China Resources': 'Unlisted central SOE; parent of several HK-listed companies.',
 'Emirates Group': "Owned by Investment Corporation of Dubai (Dubai government).",
 'REWE Group': 'Co-operative of independent grocers.', 'Edeka Zentrale': 'Co-operative of independent grocers.',
 'Mercadona': 'Roig family.', 'Saudi Aramco': '',
}
for r in inv:
    if not r['note']:
        r['note'] = NOTES.get(r['company'], '')
inv = sorted(inv, key=lambda r: -r['rev'])

# ------------------------------------------------------------------------------------------
# Largest US private companies (Forbes)
# ------------------------------------------------------------------------------------------
pv_rows = [dict(rank=int(r.rank), company=r.company, industry=r.industry, rev=r.revenue_musd, emp=None if pd.isna(r.employees) else int(r.employees),
                chg=None if pd.isna(r.revenue_change_pct) else r.revenue_change_pct, city=f'{r.city}, {r.state}',
                founded=None if pd.isna(r.year_founded) else int(r.year_founded)) for r in pv.itertuples()]
pv_stats = dict(n=len(pv), rev=round(pv.revenue_musd.sum()), emp=int(pv.employees.sum()), top10=round(pv.head(10).revenue_musd.sum()))
us_listed = g[g.country == 'United States']
pv_stats['us_g2000_rev'] = round(us_listed.revenue_musd.sum())

# ------------------------------------------------------------------------------------------
# Curated family / foundation control table
# ------------------------------------------------------------------------------------------
FAMILY = [
 # company, forbes name to join, country, controller, type, stake description
 ('Walmart', 'Walmart', 'United States', 'Walton family (Walton Enterprises / heirs)', 'Family', '~45% of shares'),
 ('Tata group (TCS, Tata Motors, Tata Steel…)', 'Tata Consultancy Services', 'India', 'Tata Trusts via Tata Sons', 'Foundation / trust', 'Trusts own ~66% of Tata Sons; Tata Sons owns ~72% of TCS'),
 ('Reliance Industries', 'Reliance Industries', 'India', 'Mukesh Ambani family (promoter group)', 'Family', '~50% promoter holding'),
 ('Adani Enterprises', 'Adani Enterprises', 'India', 'Gautam Adani family (promoter group)', 'Family', '~70%+ promoter holding'),
 ('Wipro', 'Wipro', 'India', 'Azim Premji, family and Azim Premji Foundation endowment', 'Family + foundation', '~73% promoter holding'),
 ('Novo Nordisk', 'Novo Nordisk', 'Denmark', 'Novo Nordisk Foundation via Novo Holdings', 'Foundation', '~28% of capital, ~77% of votes (dual-class)'),
 ('Carlsberg', 'Carlsberg', 'Denmark', 'Carlsberg Foundation', 'Foundation', '~30% of capital, ~75% of votes'),
 ('A.P. Moller-Maersk', 'A.P. Moller-Maersk', 'Denmark', 'A.P. Moller Holding / Maersk family foundation', 'Foundation + family', '~42% capital, ~51% votes'),
 ('Samsung Electronics', 'Samsung Electronics', 'South Korea', 'Lee family via cross-holdings (Samsung C&T, Samsung Life)', 'Family via cross-holdings', 'Family + affiliates ~20%'),
 ('Hyundai Motor', 'Hyundai Motor', 'South Korea', 'Chung family via Hyundai Mobis / Kia circular holdings', 'Family via cross-holdings', 'Group affiliates ~30%'),
 ('LVMH', 'LVMH Louis Vuitton Moet Hennessy', 'France', 'Bernard Arnault family', 'Family', '~48% of capital, ~64% of votes'),
 ('Hermès International', 'Hermès International', 'France', 'Hermes-Dumas family (H51)', 'Family', '~66% of capital'),
 ('Toyota Motor', 'Toyota Motor', 'Japan', 'Group cross-shareholdings (Toyota Industries, Denso, banks); Toyoda family <2%', 'Cross-holdings (keiretsu)', 'Toyota Industries ~9% largest holder'),
 ('Volkswagen Group', 'Volkswagen Group', 'Germany', 'Porsche-Piech families via Porsche SE; State of Lower Saxony', 'Family + state', 'Porsche SE ~53% votes; Lower Saxony 20% votes'),
 ('BMW Group', 'BMW Group', 'Germany', 'Quandt family (Stefan Quandt, Susanne Klatten)', 'Family', '~47%'),
 ('Bosch', None, 'Germany', 'Robert Bosch Stiftung (charitable foundation)', 'Foundation', '~94% of equity, no votes; Industrietreuhand holds votes'),
 ('Ingka / IKEA', None, 'Netherlands / Sweden', 'Stichting INGKA Foundation', 'Foundation', '100%'),
 ('Roche Holding', 'Roche Holding', 'Switzerland', 'Hoffmann & Oeri families (shareholder pool)', 'Family', '~50%+ of voting shares'),
 ('Inditex', 'Inditex', 'Spain', 'Amancio Ortega', 'Founder', '~59%'),
 ('Meta Platforms', 'Meta Platforms', 'United States', 'Mark Zuckerberg (Class B super-voting shares)', 'Founder (dual-class)', '~13% economic, ~61% votes'),
 ('Alphabet', 'Alphabet', 'United States', 'Larry Page & Sergey Brin (Class B)', 'Founder (dual-class)', '~6% economic, ~51% votes'),
 ('Cargill', None, 'United States', 'Cargill & MacMillan families', 'Family', '~88%'),
 ('Mars', None, 'United States', 'Mars family', 'Family', '~100%'),
 ('Koch', None, 'United States', 'Charles Koch & family of David Koch', 'Family', '~84%+'),
 ('Schwarz Group (Lidl)', None, 'Germany', 'Dieter Schwarz Stiftung', 'Foundation', '~100% economic'),
 ('Aldi', None, 'Germany', 'Albrecht family foundations (Markus-, Lukas-, Jakobus-Stiftung; Siepmann)', 'Foundation + family', '100%'),
 ('ZF Friedrichshafen', None, 'Germany', 'Zeppelin Foundation (administered by the town of Friedrichshafen)', 'Foundation', '~94%'),
 ('Heineken', 'Heineken', 'Netherlands', 'Heineken family (via Heineken Holding / L\'Arche Green)', 'Family', '~50% of Heineken Holding'),
]
gfx = g.set_index('company')
family = []
for c, fn, ctry, ctrl, typ, stake in FAMILY:
    rev = None
    mv = None
    if fn and fn in gfx.index:
        rev = float(gfx.loc[fn, 'revenue_musd']); mv = float(gfx.loc[fn, 'market_value_musd'])
    elif fn:
        hits = [x for x in gfx.index if x.lower().startswith(fn.lower()[:10])]
        if hits:
            rev = float(gfx.loc[hits[0], 'revenue_musd']); mv = float(gfx.loc[hits[0], 'market_value_musd'])
        else:
            print('WARN family join failed', fn)
    if rev is None:
        for r in inv:
            if r['company'].lower().startswith(c.lower()[:5]):
                rev = r['rev']; break
    family.append(dict(company=c, country=ctry, controller=ctrl, type=typ, stake=stake, rev=rev, mv=mv, listed=bool(fn)))

# ------------------------------------------------------------------------------------------
# headline numbers
# ------------------------------------------------------------------------------------------
fm = {r['owner']: r for r in fortune_mix}
state_all = fm['Listed, state-controlled']['rev'] + fm['State-owned, unlisted']['rev']
H = dict(
    fortune_rev=fortune_tot['rev'], fortune_n=fortune_tot['n'],
    state_ctrl_rev=state_all, state_ctrl_n=fm['Listed, state-controlled']['n'] + fm['State-owned, unlisted']['n'],
    state_ctrl_pct=round(state_all / fortune_tot['rev'] * 100, 1),
    state_any_pct=round((state_all + fm['Listed, significant state stake']['rev']) / fortune_tot['rev'] * 100, 1),
    unlisted_n=fm['State-owned, unlisted']['n'] + fm['Private (family / founder / foundation)']['n'] + fm['Mutual / co-operative']['n'],
    unlisted_rev=fm['State-owned, unlisted']['rev'] + fm['Private (family / founder / foundation)']['rev'] + fm['Mutual / co-operative']['rev'],
    china_n=int((f.country == 'China').sum()), us_n=int((f.country == 'United States').sum()),
    china_state_n=int(((f.country == 'China') & f.owner.isin(['Listed, state-controlled', 'State-owned, unlisted'])).sum()),
    china_state_rev_pct=round(f[(f.country == 'China') & f.owner.isin(['Listed, state-controlled', 'State-owned, unlisted', 'Listed, significant state stake'])].revenues_musd.sum()
                              / f[f.country == 'China'].revenues_musd.sum() * 100, 1),
    india_n=int((f.country == 'India').sum()),
    india_psu_n=int((ind.state != 'No').sum()), india_n_g2000=len(ind),
    india_psu_rev_pct=round(ind[ind.state != 'No'].revenue_musd.sum() / ind.revenue_musd.sum() * 100, 1),
    india_psu_mv_pct=round(ind[ind.state != 'No'].market_value_musd.sum() / ind.market_value_musd.sum() * 100, 1),
    india_psu_profit_pct=round(ind[ind.state != 'No'].profits_musd.sum() / ind.profits_musd.sum() * 100, 1),
    forbes_state_rev_pct=round(g[g.state != 'No'].revenue_musd.sum() / g.revenue_musd.sum() * 100, 1),
    forbes_state_m_rev_pct=round(g[g.state == 'Majority / control'].revenue_musd.sum() / g.revenue_musd.sum() * 100, 1),
    forbes_state_n=int((g.state != 'No').sum()),
    forbes_state_mv_pct=round(g[g.state != 'No'].market_value_musd.sum() / g.market_value_musd.sum() * 100, 1),
)
margin_tests = mt.to_dict(orient='records')

data = dict(H=H, own_order=OWN_ORDER, fortune_mix=fortune_mix, fortune_tot=fortune_tot, fortune_country=fortune_country,
            fortune_rows=fortune_rows, invisible=inv, state_by_country=state_by_country, india=india, india_stats=india_stats,
            china_stats=china_stats, forbes_margin=forbes_margin, private_us=pv_rows, pv_stats=pv_stats, family=family,
            margin_tests=margin_tests)

def clean(o):
    if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list): return [clean(v) for v in o]
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating, float)):
        return None if (o != o) else round(float(o), 2)
    if isinstance(o, (np.bool_,)): return bool(o)
    return o

js = 'window.ATLAS = window.ATLAS || {};\nwindow.ATLAS.ownership = ' + json.dumps(clean(data), ensure_ascii=False, separators=(',', ':')) + ';\n'
open(OUT, 'w', encoding='utf-8').write(js)
print('wrote', OUT, round(len(js) / 1024), 'KB')
print(json.dumps(clean(H), indent=1))
for r in fortune_mix: print(r)
for r in state_by_country[:25]: print(r['country'], r['pct_m'], r['pct_s'], r['n_m'], r['n_s'], r['unassessed_pct'])
print(india_stats); print(china_stats); print(forbes_margin)
