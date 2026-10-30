"""Automatic data update for the parts of Earth Economy that come from stable, official sources.

What it updates
  stock indexes (Yahoo Finance), exchange rates (US Federal Reserve / OECD via FRED, Yahoo for ARS),
  World Bank market value by country, World Bank population and GDP.
  -> rebuilds site/data/market_history.js and site/data/unicorn_density.js
  (the "how each market performed", correlation, market-size and unicorns-per-person charts)

What it does NOT update (manual, see pipeline/README.md)
  CB Insights unicorns, companiesmarketcap.com listings, Forbes / Fortune lists.

How it stays safe
  1. Downloads into pipeline/staging/ - the live data is not touched.
  2. Checks the new files (below). Any failure: live data is kept, the log says why, exit code 1.
  3. Only then backs up the old files to pipeline/backup/<date>/, copies the new ones in and rebuilds.
  4. Checks the rebuilt site data, and restores the backup if that fails.

Run by hand:  python pipeline/update.py
Scheduled:    pipeline/schedule_windows.ps1 registers a weekly Windows task
"""
import csv, json, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPE = ROOT / 'pipeline'
STAGE = PIPE / 'staging'
LOGS = PIPE / 'logs'
PY = sys.executable

# file name in staging -> live location
FILES = {
    'index_monthly.csv': ROOT / 'stock_market' / 'data' / 'index_monthly.csv',
    'fx_monthly.csv': ROOT / 'stock_market' / 'data' / 'fx_monthly.csv',
    'wb_market_history.csv': ROOT / 'stock_market' / 'data' / 'wb_market_history.csv',
    'country_pop_gdp.csv': ROOT / 'startups' / 'data' / 'country_pop_gdp.csv',
}
BUILT = [ROOT / 'site' / 'data' / 'market_history.js', ROOT / 'site' / 'data' / 'unicorn_density.js']

# Official closing levels, end of December 2024. History must never change these.
INDEX_ANCHORS = {'^GSPC': 5881.63, '^N225': 39894.54, '^FTSE': 8173.02, '^GDAXI': 19909.14, '^BSESN': 78139.01,
                 '^NSEI': 23644.80, '^HSI': 20059.95, '000001.SS': 3351.76, '^KS11': 2399.49, '^FCHI': 7380.74,
                 '^GSPTSE': 24727.94, '^BVSP': 120283.0}
# Monthly average local currency per US$, December 2024 (FRED / OECD), +-1%.
FX_ANCHORS = {'INR': 84.97, 'JPY': 153.81, 'EUR': 0.9549, 'GBP': 0.7907, 'CNY': 7.2807, 'KRW': 1440.0,
              'BRL': 6.101, 'IDR': 16035.8, 'TRY': 34.97, 'ILS': 3.62}


def read(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


class Log:
    def __init__(self):
        self.lines, self.failed = [], []

    def ok(self, msg):
        self.lines.append(f'- OK: {msg}')

    def fail(self, msg):
        self.lines.append(f'- **FAIL: {msg}**'); self.failed.append(msg)

    def note(self, msg):
        self.lines.append(f'- {msg}')

    def check(self, cond, ok_msg, fail_msg):
        (self.ok if cond else self.fail)(ok_msg if cond else fail_msg)


def validate(log):
    new = {k: read(STAGE / k) for k in FILES}
    old = {k: read(v) if v.exists() else [] for k, v in FILES.items()}

    # 1. nothing went missing
    for k in FILES:
        n, o = len(new[k]), len(old[k])
        log.check(n >= 0.98 * o and n > 0, f'{k}: {n:,} rows (was {o:,})', f'{k}: {n:,} rows, was {o:,} (lost more than 2%)')

    # 2. indexes: all present, anchors exact, nothing stale
    idx = new['index_monthly.csv']
    syms_new = {r['symbol'] for r in idx}; syms_old = {r['symbol'] for r in old['index_monthly.csv']}
    log.check(syms_old <= syms_new, f'all {len(syms_new)} indexes present', f'indexes missing: {sorted(syms_old - syms_new)}')
    close = {(r['symbol'], r['month']): float(r['close']) for r in idx}
    bad = [f'{s} {close.get((s, "2024-12"))} vs {v}' for s, v in INDEX_ANCHORS.items()
           if not close.get((s, '2024-12')) or abs(close[(s, '2024-12')] / v - 1) > 0.001]
    log.check(not bad, f'{len(INDEX_ANCHORS)} index closes for Dec 2024 match the official closes', f'index anchor mismatch: {bad}')
    last = {}
    for r in idx:
        last[r['symbol']] = max(last.get(r['symbol'], ''), r['month'])
    top = max(last.values())
    old_top = max((r['month'] for r in old['index_monthly.csv']), default='')
    log.check(top >= old_top, f'latest index month {top} (was {old_top})', f'latest month went backwards: {top} < {old_top}')
    stale = [s for s, m in last.items() if m < shift(top, -2)]
    if stale:
        log.note(f'warning: these indexes have no data in the last 2 months: {stale}')

    # 3. history must not be rewritten (except the last 3 months, which can be revised)
    cut = shift(top, -3)
    oc = {(r['symbol'], r['month']): float(r['close']) for r in old['index_monthly.csv'] if r['month'] < cut}
    changed = [k for k, v in oc.items() if k in close and abs(close[k] / v - 1) > 0.005]
    log.check(len(changed) <= 0.01 * max(len(oc), 1), f'index history stable ({len(changed)} of {len(oc):,} old values moved >0.5%)',
              f'{len(changed)} old index values changed by >0.5%, e.g. {changed[:5]}')

    # 4. exchange rates
    fx = {(r['currency'], r['month']): float(r['local_per_usd']) for r in new['fx_monthly.csv']}
    bad = [f'{c} {fx.get((c, "2024-12"))} vs {v}' for c, v in FX_ANCHORS.items()
           if not fx.get((c, '2024-12')) or abs(fx[(c, '2024-12')] / v - 1) > 0.01]
    log.check(not bad, f'{len(FX_ANCHORS)} exchange rates for Dec 2024 match official values', f'FX anchor mismatch: {bad}')

    # 5. World Bank: world total stable, countries not lost
    def wld(rows, y):
        return next((float(r['mcap_usd']) for r in rows if r['iso3'] == 'WLD' and r['year'] == str(y) and r['mcap_usd']), None)
    a, b = wld(new['wb_market_history.csv'], 2024), wld(old['wb_market_history.csv'], 2024)
    log.check(a and (not b or abs(a / b - 1) < 0.03), f'World Bank world market value 2024: ${a / 1e12:.1f}T',
              f'World Bank world 2024 changed from {b} to {a}')
    cn = lambda rows: len({r['iso3'] for r in rows if r['mcap_usd']})
    log.check(cn(new['wb_market_history.csv']) >= 0.95 * cn(old['wb_market_history.csv']),
              f'World Bank: {cn(new["wb_market_history.csv"])} economies with market data',
              'World Bank lost more than 5% of economies')
    pop = {r['iso3']: float(r['population'] or 0) for r in new['country_pop_gdp.csv']}
    log.check(3.0e8 < pop.get('USA', 0) < 4.0e8 and 1.3e9 < pop.get('IND', 0) < 1.6e9, 'population figures plausible (US, India)',
              f'population looks wrong: US {pop.get("USA")}, India {pop.get("IND")}')


def shift(m, n):
    y, mo = map(int, m.split('-')); t = y * 12 + mo - 1 + n
    return f'{t // 12}-{t % 12 + 1:02d}'


def check_built(log):
    for p in BUILT:
        txt = p.read_text(encoding='utf-8')
        try:
            d = json.loads(txt[txt.index('= {') + 2:].rstrip().rstrip(';'))
        except Exception as e:  # noqa: BLE001
            log.fail(f'{p.name} is not valid data: {e}'); continue
        if p.name == 'market_history.js':
            log.check(len(d['indexes']) >= 27 and len(d['wb']) >= 90, f'{p.name}: {len(d["indexes"])} indexes, {len(d["wb"])} economies',
                      f'{p.name}: only {len(d["indexes"])} indexes / {len(d["wb"])} economies')
        else:
            log.check(len(d) >= 50, f'{p.name}: {len(d)} countries', f'{p.name}: only {len(d)} countries')


def run(cmd, log):
    r = subprocess.run([PY] + cmd, cwd=ROOT, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip().splitlines()
    log.note(f'`{" ".join(cmd)}` -> exit {r.returncode}' + (f': {out[-1]}' if out else ''))
    return r.returncode == 0


def main():
    stamp = datetime.now().strftime('%Y-%m-%d_%H%M')
    log = Log()
    log.lines.append(f'# Data update {stamp}\n')
    LOGS.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(STAGE, ignore_errors=True); STAGE.mkdir(parents=True)

    status = 'FAILED'
    try:
        log.lines.append('## Download')
        if not run(['stock_market/scripts/fetch_history.py', '--out', str(STAGE)], log):
            log.fail('download script failed')
        else:
            log.lines.append('\n## Checks on the new data')
            validate(log)
            if not log.failed:
                log.lines.append('\n## Install and rebuild')
                backup = PIPE / 'backup' / stamp; backup.mkdir(parents=True)
                for k, live in FILES.items():
                    if live.exists():
                        shutil.copy2(live, backup / k)
                for p in BUILT:
                    if p.exists():
                        shutil.copy2(p, backup / p.name)
                for k, live in FILES.items():
                    shutil.copy2(STAGE / k, live)
                ok = run(['site/build/market_history.py'], log) and run(['site/build/unicorn_density.py'], log)
                if ok:
                    check_built(log)
                if not ok or log.failed:
                    for k, live in FILES.items():
                        if (backup / k).exists():
                            shutil.copy2(backup / k, live)
                    for p in BUILT:
                        if (backup / p.name).exists():
                            shutil.copy2(backup / p.name, p)
                    log.fail('rebuild failed; restored the previous data')
                else:
                    status = 'UPDATED'
                    # keep the 5 newest backups
                    for old in sorted((PIPE / 'backup').iterdir())[:-5]:
                        shutil.rmtree(old, ignore_errors=True)
    except Exception as e:  # noqa: BLE001
        log.fail(f'unexpected error: {e!r}')

    log.lines.insert(1, f'**Result: {status}**' + ('' if status == 'UPDATED' else ' - the site still shows the previous data') + '\n')
    text = '\n'.join(log.lines) + '\n'
    (LOGS / f'update_{stamp}.md').write_text(text, encoding='utf-8')
    (LOGS / 'latest.md').write_text(text, encoding='utf-8')
    print(text)
    sys.exit(0 if status == 'UPDATED' else 1)


if __name__ == '__main__':
    main()
