/* Stock markets page, section 8b: each country's market over time.
   Data: site/data/market_history.js (built by site/build/market_history.py). */
(function () {
const H = ATLAS.marketHistory; if (!H) return;
const P = ATLAS.palette(), U = ATLAS.fmtUSD, ACC = ATLAS.css('--accent'), GREY = ATLAS.css('--text-3');
const IX = H.indexes, LAST = H.last_month;
const label = i => i.country === 'India (NSE)' ? 'India (Nifty 50)' : i.country;
const mIdx = (i, m) => { const [y, mo] = i.start.split('-').map(Number), [Y, M] = m.split('-').map(Number); return (Y - y) * 12 + (M - mo); };
const mOf = (i, k) => { const [y, mo] = i.start.split('-').map(Number), t = y * 12 + mo - 1 + k; return `${Math.floor(t / 12)}-${String(t % 12 + 1).padStart(2, '0')}`; };
const pct = v => v == null || !isFinite(v) ? '—' : (v >= 0 ? '+' : '') + (v * 100).toFixed(1) + '%';
const times = v => v == null ? '—' : v >= 10 ? v.toFixed(0) + '×' : v.toFixed(1) + '×';
function T2(id) {
  const btn = document.getElementById(id + '-t'), box = document.getElementById(id + '-tbl');
  let rows = [], cols = [], open = false; box.hidden = true; btn.textContent = 'Show data table';
  btn.onclick = () => { open = !open; box.hidden = !open; btn.textContent = open ? 'Hide data table' : 'Show data table'; if (open) ATLAS.table(box, rows, cols); };
  return (r, c) => { rows = r; cols = c; if (open) ATLAS.table(box, rows, cols); };
}
function seg(el, opts, val, cb, lab) {
  el = document.getElementById(el);
  const box = document.createElement('span');
  box.style.cssText = 'display:inline-flex;gap:4px;flex-wrap:wrap;align-items:center';
  box.innerHTML = (lab ? `<span>${lab}</span>` : '') + opts.map(([k, t]) => `<button type="button" data-k="${k}" class="${k === val ? 'on' : ''}">${t}</button>`).join('');
  box.querySelectorAll('button').forEach(b => b.onclick = () => { box.querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b)); cb(b.dataset.k); });
  el.append(box);
}

// Growth of one index from the start year (or its first month) to the latest close.
function stats(i, cur, y0) {
  const a = i[cur]; let b = Math.max(0, mIdx(i, `${y0}-01`));
  while (b < a.length && a[b] == null) b++;
  let e = a.length - 1; while (e > b && a[e] == null) e--;
  if (b >= a.length || e <= b) return null;
  const yrs = (e - b) / 12, mult = a[e] / a[b];
  return { b, e, from: mOf(i, b), to: mOf(i, e), yrs, mult, cagr: Math.pow(mult, 1 / yrs) - 1, late: mOf(i, b) > `${y0}-01` };
}

// ---------- index performance ----------
const DEF = ['United States', 'India', 'China', 'Japan', 'United Kingdom', 'Germany', 'Brazil', 'South Korea'];
let cur = 'usd', y0 = 2000, logY = true; const sel = new Set(DEF);
const perfTbl = T2('c-perf'), rankTbl = T2('c-prank');
const tools = document.getElementById('perf-tools');
seg('perf-tools', [['usd', 'US dollars'], ['loc', 'Local currency']], cur, k => { cur = k; drawAll(); }, 'Currency');
const ys = document.createElement('label'); ys.innerHTML = 'Start year <select></select>'; tools.append(ys);
const ySel = ys.querySelector('select');
for (let y = 1985; y <= 2025; y++) ySel.insertAdjacentHTML('beforeend', `<option ${y === y0 ? 'selected' : ''}>${y}</option>`);
ySel.onchange = () => { y0 = +ySel.value; drawAll(); };
seg('perf-tools', [['log', 'Log'], ['lin', 'Linear']], 'log', k => { logY = k === 'log'; drawPerf(); }, 'Scale');
const chips = document.getElementById('perf-cty');
chips.innerHTML = IX.map(i => `<button type="button" data-c="${i.country}" class="${sel.has(i.country) ? 'on' : ''}" title="${i.name}">${label(i)}</button>`).join('');
chips.querySelectorAll('button').forEach(b => b.onclick = () => {
  const c = b.dataset.c; if (sel.has(c)) { if (sel.size > 1) sel.delete(c); } else sel.add(c);
  b.classList.toggle('on', sel.has(c)); drawPerf();
});

let perfInst;
function drawPerf() {
  const rows = [];
  const series = IX.filter(i => sel.has(i.country)).map(i => {
    const s = stats(i, cur, y0); if (!s) return null; rows.push(Object.assign({ i }, s));
    const a = i[cur], base = a[s.b], data = [];
    for (let k = s.b; k <= s.e; k++) if (a[k] != null) data.push([mOf(i, k) + '-15', +(a[k] / base * 100).toFixed(2)]);
    const d = DEF.indexOf(i.country), col = i.country === 'India' ? ACC : P[d >= 0 ? d % 8 : (IX.indexOf(i) + 3) % 8];
    return { name: label(i) + (s.late ? ` (from ${s.from.slice(0, 4)})` : ''), type: 'line', showSymbol: false, data, sampling: 'lttb',
      lineStyle: { width: i.country === 'India' ? 3 : 2, type: s.late ? 'dashed' : 'solid' }, itemStyle: { color: col } };
  }).filter(Boolean);
  const best = rows.slice().sort((a, b) => b.cagr - a.cagr)[0];
  const curTxt = cur === 'usd' ? 'in US dollars' : 'in local currency';
  document.getElementById('c-perf-h').textContent = best
    ? `Since ${y0}, ${curTxt}, ${label(best.i)} grew most of the markets shown: ${times(best.mult)}, or ${pct(best.cagr)} a year`
    : 'No data for this selection';
  document.getElementById('c-perf-sub').textContent = `Main stock index, start of ${y0} = 100, ${curTxt}, monthly to ${LAST}. Dashed lines start later and are set to 100 at their first month.`;
  if (perfInst) perfInst.dispose();
  perfInst = ATLAS.chart('c-perf', {
    legend: { data: series.map(s => s.name) }, grid: { top: 56, right: 24, bottom: 8 },
    tooltip: { trigger: 'axis', order: 'valueDesc', formatter: ps => [`<b>${ps[0].axisValueLabel.slice(0, 7)}</b>`].concat(ps.map(p => `${p.marker}${p.seriesName}: <b>${p.value[1].toFixed(0)}</b> (${times(p.value[1] / 100)})`)).join('<br>') },
    xAxis: { type: 'time', axisLabel: { formatter: '{yyyy}' } },
    yAxis: { type: logY ? 'log' : 'value', name: `${y0} = 100`, axisLabel: { formatter: v => v >= 1000 ? (v / 1000) + 'k' : v } },
    series,
  });
  perfTbl(rows.sort((a, b) => b.cagr - a.cagr).map(r => ({ market: label(r.i), index: r.i.name, from: r.from, to: r.to, mult: r.mult, cagr: r.cagr })),
    [{ key: 'market', label: 'Market' }, { key: 'index', label: 'Index' }, { key: 'from', label: 'From' }, { key: 'to', label: 'To' },
     { key: 'mult', label: 'Growth', num: true, fmt: times }, { key: 'cagr', label: 'Per year', num: true, fmt: pct }]);
}

// ---------- ranking: every index ----------
let rankInst;
function drawRank() {
  const rows = IX.map(i => { const s = stats(i, cur, y0); return s && Object.assign({ i }, s); }).filter(Boolean).sort((a, b) => b.cagr - a.cagr);
  const curTxt = cur === 'usd' ? 'in US dollars' : 'in local currency';
  const full = rows.filter(r => !r.late);
  document.getElementById('c-prank-h').textContent = full.length > 1
    ? `Since ${y0}, ${curTxt}: ${label(full[0].i)} grew fastest (${pct(full[0].cagr)} a year), ${label(full[full.length - 1].i)} slowest (${pct(full[full.length - 1].cagr)})`
    : 'Every market ranked by yearly growth';
  document.getElementById('c-prank-sub').textContent = `Compound yearly change in each main index, start of ${y0} (or first month of data) to ${LAST}, ${curTxt}. ${rows.length} of ${IX.length} indexes have data for this view.`;
  const data = rows.slice().reverse();
  if (rankInst) rankInst.dispose();
  rankInst = ATLAS.chart('c-prank', {
    grid: { top: 10, right: 64, bottom: 8 },
    tooltip: { formatter: p => { const r = data[p.dataIndex]; return `<b>${label(r.i)}</b> · ${r.i.name}<br>${r.from} to ${r.to} (${r.yrs.toFixed(1)} years)<br>Growth: <b>${times(r.mult)}</b> · <b>${pct(r.cagr)}</b> a year${r.late ? '<br><i>Data starts after ' + y0 + '</i>' : ''}`; } },
    xAxis: { type: 'value', axisLabel: { formatter: v => (v * 100).toFixed(0) + '%' } },
    yAxis: { type: 'category', data: data.map(r => label(r.i) + (r.late ? ` (${r.from.slice(0, 4)}–)` : '')), axisLabel: { fontSize: 12 } },
    series: [{ type: 'bar', barMaxWidth: 16, data: data.map(r => ({ value: +r.cagr.toFixed(4), itemStyle: { color: r.i.country.startsWith('India') ? ACC : P[0], opacity: r.late ? 0.45 : 1 } })),
      label: { show: true, position: 'right', fontSize: 11, formatter: p => pct(p.value) } }],
  });
  rankTbl(rows.map(r => ({ market: label(r.i), index: r.i.name, cur: r.i.cur, from: r.from, mult: r.mult, cagr: r.cagr })),
    [{ key: 'market', label: 'Market' }, { key: 'index', label: 'Index' }, { key: 'cur', label: 'Currency' }, { key: 'from', label: 'From' },
     { key: 'mult', label: 'Growth', num: true, fmt: times }, { key: 'cagr', label: 'Per year', num: true, fmt: pct }]);
}
function drawAll() { drawPerf(); drawRank(); }
drawAll();

// Writer's notes are computed from the data, so they stay true after a rebuild.
(function () {
  const g = (c, k, y) => { const i = IX.find(x => x.country === c); return i && stats(i, k, y); };
  const us = g('United States', 'usd', 2000), inU = g('India', 'usd', 2000), inL = g('India', 'loc', 2000), cn = g('China', 'usd', 2000),
    jp = g('Japan', 'loc', 1990), arL = g('Argentina', 'loc', 2002), arU = g('Argentina', 'usd', 2002), uk = g('United Kingdom', 'loc', 2000);
  ATLAS.notes('n-perf', { items: [
    us && inU && inL && `<b>India vs the US since 2000:</b> the Sensex grew ${times(inL.mult)} in rupees (${pct(inL.cagr)} a year) but ${times(inU.mult)} in dollars (${pct(inU.cagr)}), because the rupee lost value against the dollar. The S&P 500 grew ${times(us.mult)} (${pct(us.cagr)}). Always say which currency you mean.`,
    cn && `<b>China's paradox:</b> the world's second-largest economy, yet the Shanghai Composite grew only ${times(cn.mult)} in dollars since 2000 (${pct(cn.cagr)} a year). Fast GDP growth did not turn into index growth.`,
    jp && `<b>Japan's lost decades:</b> from the start of 1990 the Nikkei 225 is up ${times(jp.mult)} in yen (${pct(jp.cagr)} a year). It only passed its December 1989 peak in February 2024.`,
    arL && arU && `<b>Inflation fools the local view:</b> Argentina's Merval rose ${times(arL.mult)} in pesos since 2002 but ${times(arU.mult)} in dollars. Use the US-dollar view for Argentina, Turkey and Brazil before 1995.`,
    uk && `<b>Dividends are not counted.</b> These are price indexes. UK and European companies pay out more of their profit as dividends, so the FTSE 100's ${pct(uk.cagr)} a year since 2000 understates what investors earned by roughly 3–4 points a year.`,
  ].filter(Boolean) });
})();

// ---------- market size (World Bank) ----------
const WB = H.wb, byIso = Object.fromEntries(WB.map(c => [c.iso, c]));
const SDEF = ['WLD', 'USA', 'CHN', 'JPN', 'IND', 'GBR', 'HKG', 'SAU'].filter(i => byIso[i]);
let sm = 'mcap'; const ssel = new Set(SDEF);
const sizeTbl = T2('c-size');
seg('size-tools', [['mcap', 'Market value, US$'], ['pct', '% of GDP']], sm, k => { sm = k; drawSize(); }, 'Measure');
const add = document.createElement('label');
add.innerHTML = 'Add a country <select><option value="">Choose…</option>' + WB.slice().sort((a, b) => a.name.localeCompare(b.name)).map(c => `<option value="${c.iso}">${c.name}</option>`).join('') + '</select>';
document.getElementById('size-tools').append(add);
add.querySelector('select').onchange = e => { if (e.target.value) { ssel.add(e.target.value); e.target.value = ''; drawSize(); } };
const lastYear = c => Math.max(...Object.keys(c.mcap).map(Number));
let sizeInst;
function drawSize() {
  const box = document.getElementById('size-cty');
  box.innerHTML = [...ssel].map(iso => `<button type="button" class="on x" data-i="${iso}" title="Remove">${byIso[iso].name}</button>`).join('');
  box.querySelectorAll('button').forEach(b => b.onclick = () => { if (ssel.size > 1) { ssel.delete(b.dataset.i); drawSize(); } });
  const cs = [...ssel].map(i => byIso[i]);
  const years = []; for (let y = 1975; y <= 2025; y++) years.push(y);
  const fmt = v => sm === 'mcap' ? U(v, 'usd', v >= 1e12 ? 1 : 0) : v.toFixed(0) + '%';
  document.getElementById('c-size-sub').textContent = sm === 'mcap'
    ? 'Market value of listed domestic companies, current US$, end of year, log scale. Gaps are years with no data.'
    : 'Market value of listed domestic companies as % of GDP, end of year. Gaps are years with no data.';
  const w = byIso.WLD, wl = lastYear(w);
  document.getElementById('c-size-h').textContent = `World stock markets were worth ${U(w.mcap[wl])} in ${wl}, up from ${U(w.mcap[1975])} in 1975; the US alone was ${U(byIso.USA.mcap[wl])}`;
  if (sizeInst) sizeInst.dispose();
  sizeInst = ATLAS.chart('c-size', {
    legend: { data: cs.map(c => c.name) }, grid: { top: 56, right: 24, bottom: 8 },
    tooltip: { trigger: 'axis', order: 'valueDesc', formatter: ps => [`<b>${ps[0].axisValue}</b>`].concat(ps.filter(p => p.value != null).map(p => `${p.marker}${p.seriesName}: <b>${fmt(p.value)}</b>`)).join('<br>') },
    xAxis: { type: 'category', data: years, boundaryGap: false },
    yAxis: { type: sm === 'mcap' ? 'log' : 'value', axisLabel: { formatter: v => sm === 'mcap' ? U(v, 'usd', 0) : v + '%' } },
    series: cs.map((c, n) => ({ name: c.name, type: 'line', showSymbol: false, connectNulls: false, data: years.map(y => c[sm][y] ?? null),
      lineStyle: { width: c.iso === 'IND' || c.iso === 'WLD' ? 3 : 2 }, itemStyle: { color: c.iso === 'IND' ? ACC : c.iso === 'WLD' ? GREY : P[n % 8] } })),
  });
  sizeTbl(WB.map(c => { const ks = Object.keys(c.mcap).map(Number), f = Math.min(...ks), l = Math.max(...ks);
    return { name: c.name, first: f, v2000: c.mcap[2000] ?? null, v2010: c.mcap[2010] ?? null, last: l, v_last: c.mcap[l], pct: c.pct[l] ?? null,
      g: c.mcap[2000] && l >= 2020 ? c.mcap[l] / c.mcap[2000] : null }; }),
    [{ key: 'name', label: 'Country' }, { key: 'first', label: 'Data from', num: true }, { key: 'v2000', label: '2000', num: true, fmt: v => U(v) },
     { key: 'v2010', label: '2010', num: true, fmt: v => U(v) }, { key: 'last', label: 'Latest year', num: true }, { key: 'v_last', label: 'Latest value', num: true, fmt: v => U(v) },
     { key: 'g', label: 'Growth since 2000', num: true, fmt: v => v == null ? '—' : times(v) }, { key: 'pct', label: '% of GDP', num: true, fmt: v => v == null ? '—' : v.toFixed(0) + '%' }]);
}
drawSize();
const dp = H.dropped_points.map(d => `${d.iso} ${d.year}: ${d.why}`), dc = H.dropped_countries.map(d => `${d.iso} (all years): ${d.why}`);
ATLAS.notes('n-size', { title: 'Caveats: what is missing or removed, and why', caveat: true, items: [
  '<b>Not every stock market has free index history.</b> Saudi Arabia, Thailand, the Philippines, Vietnam and Russia are missing from the index charts, but appear in the market-size chart. For India the Sensex is used because free Nifty 50 history starts only in 2007.',
  '<b>World Bank market value mixes three things:</b> share prices, new listings and the exchange rate. A market can jump because a giant listed (Saudi Aramco, December 2019) or shrink because its currency fell.',
  '<b>Removed as reporting errors:</b> ' + dp.concat(dc).join('; ') + '.',
  `<b>Latest data:</b> the World Bank series runs to 2025 for most countries (the UK stops in 2022). Index data runs to ${LAST}.`,
] });
})();
