"""Download the history behind the "how each stock market grew" section.

Writes (all under stock_market/data/):
  wb_market_history.csv  World Bank, every country, 1975-latest: market cap (US$), market cap % GDP,
                         number of listed domestic companies (WFE data via WDI)
  index_monthly.csv      month-end close of each country's main stock index (Yahoo Finance)
  fx_monthly.csv         monthly average local currency per US$ (FRED H.10/G.5, Yahoo FX to fill gaps)
  country_pop_gdp.csv    World Bank population and GDP, latest year, for per-capita ratios

Run:  python stock_market/scripts/fetch_history.py [--out DIR]
"""
import csv, json, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'stock_market' / 'data'
POP_OUT = ROOT / 'startups' / 'data' / 'country_pop_gdp.csv'
UA = {'User-Agent': 'Mozilla/5.0'}

# country, index name, Yahoo symbol, currency, FRED series, FRED quote ('per_usd' = local per US$, 'usd_per' = US$ per local)
INDEXES = [
    ('United States', 'S&P 500', '^GSPC', 'USD', None, None),
    ('Japan', 'Nikkei 225', '^N225', 'JPY', 'EXJPUS', 'per_usd'),
    ('United Kingdom', 'FTSE 100', '^FTSE', 'GBP', 'EXUSUK', 'usd_per'),
    ('Germany', 'DAX', '^GDAXI', 'EUR', 'EUR', None),
    ('France', 'CAC 40', '^FCHI', 'EUR', 'EUR', None),
    ('Netherlands', 'AEX', '^AEX', 'EUR', 'EUR', None),
    ('Spain', 'IBEX 35', '^IBEX', 'EUR', 'EUR', None),
    ('Italy', 'FTSE MIB', 'FTSEMIB.MI', 'EUR', 'EUR', None),
    ('Switzerland', 'SMI', '^SSMI', 'CHF', 'EXSZUS', 'per_usd'),
    ('Sweden', 'OMX Stockholm 30', '^OMX', 'SEK', 'EXSDUS', 'per_usd'),
    ('India', 'BSE Sensex', '^BSESN', 'INR', 'EXINUS', 'per_usd'),
    ('India (NSE)', 'Nifty 50', '^NSEI', 'INR', 'EXINUS', 'per_usd'),
    ('China', 'Shanghai Composite', '000001.SS', 'CNY', 'EXCHUS', 'per_usd'),
    ('Hong Kong', 'Hang Seng', '^HSI', 'HKD', 'EXHKUS', 'per_usd'),
    ('Taiwan', 'TAIEX', '^TWII', 'TWD', 'EXTAUS', 'per_usd'),
    ('South Korea', 'KOSPI', '^KS11', 'KRW', 'EXKOUS', 'per_usd'),
    ('Singapore', 'Straits Times', '^STI', 'SGD', 'EXSIUS', 'per_usd'),
    ('Indonesia', 'Jakarta Composite', '^JKSE', 'IDR', 'CCUSMA02IDM618N', 'per_usd'),
    ('Malaysia', 'FTSE Bursa Malaysia KLCI', '^KLSE', 'MYR', 'EXMAUS', 'per_usd'),
    ('Australia', 'S&P/ASX 200', '^AXJO', 'AUD', 'EXUSAL', 'usd_per'),
    ('Canada', 'S&P/TSX Composite', '^GSPTSE', 'CAD', 'EXCAUS', 'per_usd'),
    ('Brazil', 'Bovespa', '^BVSP', 'BRL', 'EXBZUS', 'per_usd'),
    ('Mexico', 'S&P/BMV IPC', '^MXX', 'MXN', 'EXMXUS', 'per_usd'),
    ('Argentina', 'Merval', '^MERV', 'ARS', None, None),
    ('Israel', 'TA-35', 'TA35.TA', 'ILS', 'CCUSMA02ILM618N', 'per_usd'),
    ('Turkey', 'BIST 100', 'XU100.IS', 'TRY', 'CCUSMA02TRM618N', 'per_usd'),
    ('South Africa', 'FTSE/JSE All Share', '^J203.JO', 'ZAR', 'EXSFUS', 'per_usd'),
]
# Pre-euro legacy currencies: FRED series and the fixed conversion rate to the euro (1 EUR = x legacy units)
LEGACY = {'Germany': ('EXGEUS', 1.95583), 'France': ('EXFRUS', 6.55957), 'Netherlands': ('EXNEUS', 2.20371),
          'Spain': ('EXSPUS', 166.386), 'Italy': ('EXITUS', 1936.27)}
# Thailand, Philippines, Saudi Arabia and Vietnam have no free index history on Yahoo, so they are left out here
# (they still appear in the World Bank market-size series).
# Argentina's peso is not in FRED, so it comes from Yahoo (glitches are removed in site/build/market_history.py).
# IDR, ILS and TRY use OECD monthly averages via FRED: Yahoo had wrong values (IDR 9,500 for June 2001 vs 11,306 official).
YAHOO_FX = {'ARS': 'ARS=X'}


def get(url, tries=3):
    # FRED stalls on browser-like user agents, so it gets a plain one
    hdr = {'User-Agent': 'curl/8.0'} if 'stlouisfed' in url else UA
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=60) as r:
                return r.read().decode('utf-8')
        except Exception as e:  # noqa: BLE001 - retry any network error
            if i == tries - 1:
                raise
            time.sleep(2 + 3 * i)


def yahoo_monthly(sym):
    j = json.loads(get(f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.request.quote(sym)}?period1=-1500000000&period2=1900000000&interval=1mo'))
    res = j['chart']['result']
    if not res:
        return {}
    r = res[0]
    ts, close = r.get('timestamp') or [], r['indicators']['quote'][0].get('close') or []
    # Bars are stamped at local midnight on the 1st, so read them in the exchange's time zone,
    # otherwise Asian/European months shift back by one.
    off = r['meta'].get('gmtoffset') or 0
    out = {}
    for t, c in zip(ts, close):
        if c is None:
            continue
        out[datetime.fromtimestamp(t + off, tz=timezone.utc).strftime('%Y-%m')] = c
    return out


def fred_monthly(sid):
    txt = get(f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}')
    out = {}
    for row in list(csv.reader(txt.splitlines()))[1:]:
        if len(row) == 2 and row[1] not in ('', '.'):
            out[row[0][:7]] = float(row[1])
    return out


def wb(indicator, date='1975:2025'):
    rows, page = [], 1
    while True:
        j = json.loads(get(f'https://api.worldbank.org/v2/country/all/indicator/{indicator}?format=json&per_page=20000&date={date}&page={page}'))
        rows += j[1] or []
        if page >= j[0]['pages']:
            return rows
        page += 1


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    POP_OUT.parent.mkdir(parents=True, exist_ok=True)

    # ---- World Bank market history ----
    data = {}
    for ind, key in [('CM.MKT.LCAP.CD', 'mcap_usd'), ('CM.MKT.LCAP.GD.ZS', 'mcap_pct_gdp'), ('CM.MKT.LDOM.NO', 'n_listed')]:
        for r in wb(ind):
            if r['value'] is None or not r['countryiso3code']:
                continue
            k = (r['countryiso3code'], r['country']['value'], int(r['date']))
            data.setdefault(k, {})[key] = r['value']
    with open(OUT / 'wb_market_history.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['iso3', 'country', 'year', 'mcap_usd', 'mcap_pct_gdp', 'n_listed'])
        for (iso, name, y), v in sorted(data.items()):
            w.writerow([iso, name, y, v.get('mcap_usd'), v.get('mcap_pct_gdp'), v.get('n_listed')])
    print('world bank rows', len(data))

    # ---- population + GDP (latest year with data) ----
    pg = {}
    for ind, key in [('SP.POP.TOTL', 'population'), ('NY.GDP.MKTP.CD', 'gdp_usd')]:
        for r in wb(ind, '2022:2025'):
            if r['value'] is None or not r['countryiso3code']:
                continue
            d = pg.setdefault((r['countryiso3code'], r['country']['value']), {})
            if int(r['date']) > d.get(key + '_year', 0):
                d[key], d[key + '_year'] = r['value'], int(r['date'])
    with open(POP_OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['iso3', 'country', 'population', 'population_year', 'gdp_usd', 'gdp_year'])
        for (iso, name), d in sorted(pg.items()):
            w.writerow([iso, name, d.get('population'), d.get('population_year'), d.get('gdp_usd'), d.get('gdp_usd_year')])
    print('pop/gdp countries', len(pg))

    # ---- indexes ----
    with open(OUT / 'index_monthly.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['country', 'index', 'symbol', 'currency', 'month', 'close'])
        for country, name, sym, cur, _, _ in INDEXES:
            try:
                s = yahoo_monthly(sym)
            except Exception as e:  # noqa: BLE001
                print('  FAIL', sym, e); s = {}
            print(f'  {sym:12} {len(s):4} months', min(s) if s else '', max(s) if s else '')
            for m in sorted(s):
                w.writerow([country, name, sym, cur, m, round(s[m], 4)])
            time.sleep(0.6)

    # ---- FX: local currency per US$ ----
    fx = {}
    eur = {m: 1 / v for m, v in fred_monthly('EXUSEU').items()}  # EUR per USD from 1999
    fx['EUR'] = dict(eur)
    for country, (sid, rate) in LEGACY.items():  # synthetic EUR per USD before 1999, per country
        fx['EUR:' + country] = {m: v / rate for m, v in fred_monthly(sid).items() if m < '1999-01'}
    seen = set()
    for country, name, sym, cur, sid, q in INDEXES:
        if not sid or sid == 'EUR' or cur in seen:
            continue
        seen.add(cur)
        s = fred_monthly(sid)
        fx[cur] = {m: (1 / v if q == 'usd_per' else v) for m, v in s.items()}
    for cur, sym in YAHOO_FX.items():
        try:
            fx[cur] = yahoo_monthly(sym)
        except Exception as e:  # noqa: BLE001
            print('  FX FAIL', sym, e)
    with open(OUT / 'fx_monthly.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['currency', 'month', 'local_per_usd'])
        for cur in sorted(fx):
            for m in sorted(fx[cur]):
                w.writerow([cur, m, round(fx[cur][m], 6)])
    print('fx series', {k: (min(v), len(v)) for k, v in fx.items() if v})


if __name__ == '__main__':
    import sys
    # --out DIR writes all four files into DIR instead (used by pipeline/update.py to stage and check first)
    if '--out' in sys.argv:
        OUT = Path(sys.argv[sys.argv.index('--out') + 1]).resolve()
        POP_OUT = OUT / 'country_pop_gdp.csv'
    main()
