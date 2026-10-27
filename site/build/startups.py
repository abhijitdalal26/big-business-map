"""Build site/data/startups.js  ->  window.ATLAS.startups = {...}
Sources: startups/data/unicorns_cbinsights.csv (CB Insights unicorn board),
data/startups_2025.csv (Forbes Cloud 100 + Next Billion-Dollar Startups 2025),
ai_labs/data/ai_companies.csv, ai_labs/data/ai_labs.csv,
data_analysis/output/data/capital__top_listed.csv, capital__financial_depth.csv,
listed_universe/data/listed_universe.csv.
Run from anywhere:  python site/build/startups.py
"""
import json, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'site' / 'data' / 'startups.js'


def rd(p):
    return pd.read_csv(ROOT / p, encoding='utf-8-sig')


def clean(v):
    if v is None:
        return None
    if isinstance(v, float):
        if pd.isna(v):
            return None
        return round(v, 4)
    return v


# ---------------- unicorns ----------------
u = rd('startups/data/unicorns_cbinsights.csv')
d = pd.to_datetime(u['date_joined'], format='mixed', errors='coerce')
# 2-digit years like 8/19/26 parse fine with mixed; guard against far-future parsing
d = d.where(d.dt.year <= 2026, d - pd.DateOffset(years=100))
u['year'] = d.dt.year
u['month'] = d.dt.month

CITY = {'Gurgaon': 'Gurugram', 'Bangalore': 'Bengaluru', 'New Delhi': 'Delhi', 'Bombay': 'Mumbai'}
u['city'] = u['city'].replace(CITY)
u['country'] = u['country'].fillna('Unknown')
u['industry'] = u['industry'].fillna('Unclassified')

ALIAS = {
    'Kleiner Perkins Caufield & Byers': 'Kleiner Perkins', 'Softbank': 'SoftBank Group', 'SoftBank': 'SoftBank Group',
    'Google Ventures': 'GV', 'Kalaari Capital': 'Kalaari Capital', 'Kaalari Capital': 'Kalaari Capital',
    'Andreessen Horowitz.': 'Andreessen Horowitz', 'a16z': 'Andreessen Horowitz',
    'Tiger Global': 'Tiger Global Management', 'Matrix Partners India': 'Matrix Partners India (Z47)',
    'Sequoia Capital Israel': 'Sequoia Capital',
}


def inv_list(s):
    if not isinstance(s, str):
        return []
    parts = [p.strip().strip('.') for p in re.split(r',| and ', s) if p.strip()]
    return [ALIAS.get(p, p) for p in parts if len(p) > 1]


u['inv'] = u['investors'].apply(inv_list)

# founding year where we can find it (Forbes lists + AI registry) for time-to-unicorn
s25 = rd('data/startups_2025.csv')
ai = rd('ai_labs/data/ai_companies.csv')
fy = {}
for _, r in s25.dropna(subset=['year_founded']).iterrows():
    fy[r['company'].lower()] = int(r['year_founded'])
for _, r in ai.iterrows():
    try:
        y = int(str(r['founded'])[:4])
        fy.setdefault(str(r['company']).lower(), y)
    except Exception:
        pass
u['founded'] = u['company'].str.lower().map(fy)

uni = []
for _, r in u.iterrows():
    uni.append([r['company'], clean(float(r['valuation_busd'])),
                None if pd.isna(r['year']) else int(r['year']),
                None if pd.isna(r['month']) else int(r['month']),
                r['country'], clean(r['city']) if isinstance(r['city'], str) else None,
                r['industry'], r['inv'],
                None if pd.isna(r['founded']) else int(r['founded'])])

# ---------------- Forbes Cloud 100 / Next Billion ----------------
forbes = []
for _, r in s25.iterrows():
    desc = r['description'] if isinstance(r['description'], str) else ''
    desc = re.sub(r'\s+', ' ', desc)
    if len(desc) > 220:
        desc = desc[:217].rsplit(' ', 1)[0] + '…'
    forbes.append({
        'list': r['list'], 'rank': clean(r['rank']), 'company': r['company'], 'country': clean(r['country']),
        'city': clean(r['city']), 'industry': clean(r['industry']), 'founded': clean(r['year_founded']),
        'val_m': clean(r['valuation_musd']), 'fund_m': clean(r['funding_musd']), 'emp': clean(r['employees']),
        'ceo': clean(r['ceo']), 'desc': desc,
    })

# ---------------- AI ----------------
def modality_group(m):
    m = str(m).lower()
    if m.startswith('llm') or 'embeddings' in m or 'speech / llm' in m or 'agents / llm' in m:
        return 'LLMs'
    for key, g in [('chip', 'Chips & hardware'), ('lithograph', 'Chips & hardware'), ('robot', 'Robotics'),
                   ('autonom', 'Autonomy'), ('video', 'Image, video & 3D'), ('image', 'Image, video & 3D'),
                   ('3d', 'Image, video & 3D'), ('world model', 'Image, video & 3D'), ('biolog', 'Biology & health'),
                   ('health', 'Biology & health'), ('code', 'Code & agents'), ('agent', 'Code & agents'),
                   ('audio', 'Audio, voice & music'), ('music', 'Audio, voice & music'), ('speech', 'Audio, voice & music'),
                   ('translation', 'Audio, voice & music'), ('infra', 'Infra, data & search'), ('data', 'Infra, data & search'),
                   ('search', 'Infra, data & search'), ('memory', 'Infra, data & search'), ('enterprise', 'Enterprise AI'),
                   ('research', 'LLMs')]:
        if key in m:
            return g
    return 'Other'


aic = []
for _, r in ai.iterrows():
    try:
        f = int(str(r['founded'])[:4])
    except Exception:
        f = None
    aic.append({'company': r['company'], 'modality': clean(r['modality']), 'group': modality_group(r['modality']),
                'category': clean(r['category']), 'country': clean(r['country']), 'founded': f,
                'status': clean(r['status']), 'parent': clean(r['parent']), 'open': clean(r['open_weights']),
                'val_b': clean(r['valuation_busd_cb']), 'ticker': clean(r['ticker'])})

labs = rd('ai_labs/data/ai_labs.csv')
hf = []
for _, r in labs.dropna(subset=['hf_top_downloads']).sort_values('hf_top_downloads', ascending=False).iterrows():
    hf.append({'lab': r['lab'], 'country': clean(r['country']), 'open': clean(r['open_weights']),
               'models': clean(r['hf_models']), 'top_model': clean(r['hf_top_model']),
               'downloads': clean(r['hf_top_downloads']), 'category': clean(r['category'])})

# ---------------- public comparators ----------------
top = rd('data_analysis/output/data/capital__top_listed.csv')
NAME = {'NVIDIA CORP': 'NVIDIA', 'Apple Inc.': 'Apple', 'Alphabet Inc.': 'Alphabet', 'MICROSOFT CORPORATION': 'Microsoft',
        'AMAZON.COM, INC.': 'Amazon', 'Meta Platforms, Inc.': 'Meta', 'Broadcom Inc.': 'Broadcom', 'Tesla, Inc.': 'Tesla',
        'BERKSHIRE HATHAWAY INC': 'Berkshire Hathaway'}
listed_top = [{'company': NAME.get(r['company'], r['company']), 'country': r['country'], 'mcap_b': round(r['market_cap_usd'] / 1e9, 1)}
              for _, r in top.head(12).iterrows()]
lu = rd('listed_universe/data/listed_universe.csv')
for nm in ['Reliance Industries', 'HDFC BANK LIMITED', 'Tata Consultancy Services']:
    row = lu[lu['company'] == nm]
    if len(row):
        listed_top.append({'company': {'HDFC BANK LIMITED': 'HDFC Bank'}.get(nm, nm), 'country': 'India',
                           'mcap_b': round(float(row['market_cap_usd'].iloc[0]) / 1e9, 1)})
fd = rd('data_analysis/output/data/capital__financial_depth.csv').sort_values('market_cap', ascending=False)
markets = [{'country': r['country'], 'mcap_b': round(r['market_cap'] / 1e9, 1), 'companies': int(r['companies'])}
           for _, r in fd.head(15).iterrows()]
listed_total_b = round(float(lu['market_cap_usd'].sum()) / 1e9, 1)

# ---------------- curated latest marks (outside CB dataset) ----------------
latest = [
    {'company': 'Anthropic', 'mark_b': 965, 'date': '2026-05-28', 'event': 'Series H, $65B raised (post-money)',
     'source': 'Bloomberg, 28 May 2026 ("Anthropic Raises at $965 Billion Valuation, Eclipsing OpenAI")'},
    {'company': 'OpenAI', 'mark_b': 852, 'date': '2026-03', 'event': 'Funding round, post-money',
     'source': 'Reported March 2026 (cited by Bloomberg/W.Media coverage of Anthropic round); CB board shows $840B'},
    {'company': 'SpaceX (incl. xAI)', 'mark_b': 1250, 'date': '2026-02', 'event': 'All-stock merger with xAI (SpaceX ~$1T + xAI ~$250B); later listed',
     'source': 'Reuters-sourced reports, Feb–Apr 2026; SpaceX now carries a public market cap of ~$1.95T in this atlas’s listed universe'},
    {'company': 'ByteDance', 'mark_b': 330, 'date': '2025-08', 'event': 'Last confirmed employee tender (CB board carries $480B)',
     'source': 'StockAnalysis private-company page (tender, Aug 2025)'},
    {'company': 'Stripe', 'mark_b': 159, 'date': '2026-02', 'event': 'Employee tender offer',
     'source': 'Stripe annual letter via The Block, Feb 2026'},
]

# ---------------- headline stats ----------------
total_b = float(u['valuation_busd'].sum())
payload = {
    'meta': {'n_unicorns': int(len(u)), 'total_b': round(total_b, 1), 'median_b': float(u['valuation_busd'].median()),
             'n_countries': int(u.loc[u['country'] != 'Unknown', 'country'].nunique()), 'vintage': 'CB Insights Unicorn Board, snapshot with joins up to ' +
             str(d.max().date()), 'founded_coverage': int(u['founded'].notna().sum()),
             'listed_total_b': listed_total_b},
    'cols': ['company', 'val_b', 'year', 'month', 'country', 'city', 'industry', 'investors', 'founded'],
    'unicorns': uni,
    'forbes': forbes,
    'ai': aic,
    'hf': hf,
    'listed_top': listed_top,
    'markets': markets,
    'latest': latest,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
txt = 'window.ATLAS = window.ATLAS || {};\nwindow.ATLAS.startups = ' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ';\n'
OUT.write_text(txt, encoding='utf-8')
print(OUT, f'{len(txt)/1e6:.2f} MB', 'unicorns', len(uni), 'founded known', payload['meta']['founded_coverage'])
