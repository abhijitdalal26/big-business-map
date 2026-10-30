/* Stock markets page: how the world's markets move together.
   Uses the same index data as market_history.js (site/data/market_history.js). */
(function () {
const H = ATLAS.marketHistory; if (!H || !document.getElementById('c-corr')) return;
const P = ATLAS.palette(), ACC = ATLAS.css('--accent'), TXT2 = ATLAS.css('--text-2');
const [NEG, MID, POS] = ATLAS.diverging();
const LAST = H.last_month;

// One index per country (Sensex for India), grouped by region so related markets sit together.
const ORDER = [
  ['Americas', ['United States', 'Canada', 'Mexico', 'Brazil', 'Argentina']],
  ['Europe', ['United Kingdom', 'Germany', 'France', 'Netherlands', 'Switzerland', 'Spain', 'Italy', 'Sweden']],
  ['Middle East & Africa', ['Israel', 'Turkey', 'South Africa']],
  ['Asia-Pacific', ['Japan', 'Australia', 'Hong Kong', 'Singapore', 'South Korea', 'Taiwan', 'China', 'India', 'Indonesia', 'Malaysia']],
];
const byC = Object.fromEntries(H.indexes.map(i => [i.country, i]));
const MK = ORDER.flatMap(([, cs]) => cs).filter(c => byC[c]);
const regionOf = Object.fromEntries(ORDER.flatMap(([r, cs]) => cs.map(c => [c, r])));

// monthly % changes keyed by 'YYYY-MM'
const mOf = (i, k) => { const [y, mo] = i.start.split('-').map(Number), t = y * 12 + mo - 1 + k; return `${Math.floor(t / 12)}-${String(t % 12 + 1).padStart(2, '0')}`; };
function returns(i, cur) {
  const a = i[cur], out = {};
  for (let k = 1; k < a.length; k++) if (a[k] != null && a[k - 1] != null) out[mOf(i, k)] = a[k] / a[k - 1] - 1;
  return out;
}
const RET = { usd: {}, loc: {} };
MK.forEach(c => { RET.usd[c] = returns(byC[c], 'usd'); RET.loc[c] = returns(byC[c], 'loc'); });
const shift = (m, n) => { const [y, mo] = m.split('-').map(Number), t = y * 12 + mo - 1 + n; return `${Math.floor(t / 12)}-${String(t % 12 + 1).padStart(2, '0')}`; };

function corr(a, b, from, to) {
  let n = 0, sx = 0, sy = 0, sxx = 0, syy = 0, sxy = 0;
  for (const m in a) {
    if (m < from || m > to || !(m in b)) continue;
    const x = a[m], y = b[m]; n++; sx += x; sy += y; sxx += x * x; syy += y * y; sxy += x * y;
  }
  if (n < 24) return null;
  const v = (n * sxy - sx * sy) / Math.sqrt((n * sxx - sx * sx) * (n * syy - sy * sy));
  return isFinite(v) ? { r: v, n } : null;
}

const PERIODS = [['5y', 'Last 5 years', shift(LAST, -60)], ['10y', 'Last 10 years', shift(LAST, -120)],
  ['2000s', '2000–2009', '2000-01', '2009-12'], ['all', 'Since 1990', '1990-01']];
let per = '10y', cur = 'usd';
const fmt = v => v == null ? '—' : v.toFixed(2);
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
const span = () => { const p = PERIODS.find(x => x[0] === per); return [p[2], p[3] || LAST, p[1]]; };
const corrTbl = T2('c-corr'), usTbl = T2('c-cus'), rollTbl = T2('c-croll');
seg('corr-tools', PERIODS.map(p => [p[0], p[1]]), per, k => { per = k; draw(); }, 'Period');
seg('corr-tools', [['usd', 'US dollars'], ['loc', 'Local currency']], cur, k => { cur = k; draw(); }, 'Currency');

let hInst, uInst;
function draw() {
  const [from, to, lab] = span(), R = RET[cur];
  const M = MK.map(a => MK.map(b => corr(R[a], R[b], from, to)));
  const data = [], pairs = [];
  MK.forEach((a, i) => MK.forEach((b, j) => {
    const c = M[i][j]; data.push([j, i, c ? +c.r.toFixed(2) : '-']);
    if (j > i && c) pairs.push({ a, b, r: c.r, n: c.n, same: regionOf[a] === regionOf[b] });
  }));
  pairs.sort((x, y) => y.r - x.r);
  const avg = pairs.reduce((s, p) => s + p.r, 0) / pairs.length;
  const inReg = pairs.filter(p => p.same), cross = pairs.filter(p => !p.same);
  const mean = a => a.reduce((s, p) => s + p.r, 0) / a.length;
  const curTxt = cur === 'usd' ? 'in US dollars' : 'in local currency';
  document.getElementById('c-corr-h').textContent = pairs.length
    ? `${lab}: the average pair of markets has a correlation of ${fmt(avg)}; markets in the same region ${fmt(mean(inReg))}, across regions ${fmt(mean(cross))}`
    : 'Not enough data for this period';
  document.getElementById('c-corr-sub').textContent = `Correlation of monthly index returns, ${from} to ${to}, ${curTxt}. Hover a square for the pair.`;
  const phone = window.matchMedia('(max-width: 640px)').matches;
  if (hInst) hInst.dispose();
  hInst = ATLAS.chart('c-corr', {
    grid: { top: 8, left: 8, right: 8, bottom: 60, containLabel: true },
    tooltip: { formatter: p => { const a = MK[p.value[1]], b = MK[p.value[0]], c = M[p.value[1]][p.value[0]];
      return c ? `<b>${a} × ${b}</b><br>Correlation <b>${fmt(c.r)}</b><br>${c.n} shared months` : `${a} × ${b}<br>Not enough shared months`; } },
    xAxis: { type: 'category', data: MK, axisLabel: { rotate: 60, fontSize: phone ? 9 : 11, interval: 0 }, splitArea: { show: false } },
    yAxis: { type: 'category', data: MK, inverse: true, axisLabel: { fontSize: phone ? 9 : 11, interval: 0 } },
    visualMap: { min: -0.2, max: 1, calculable: false, orient: 'horizontal', left: 'center', bottom: 0, itemHeight: 160, itemWidth: 10,
      text: ['1 = move together', '0'], textStyle: { color: TXT2, fontSize: 11 }, inRange: { color: [NEG, MID, POS] } },
    series: [{ type: 'heatmap', data, label: { show: !phone, fontSize: 8, formatter: p => p.value[2] === '-' || p.value[0] === p.value[1] ? '' : Math.round(p.value[2] * 100) / 100 },
      itemStyle: { borderColor: ATLAS.css('--surface'), borderWidth: 1 } }],
  });
  corrTbl(pairs.map(p => ({ pair: `${p.a} × ${p.b}`, r: p.r, n: p.n, same: p.same ? 'yes' : 'no' })),
    [{ key: 'pair', label: 'Pair' }, { key: 'r', label: 'Correlation', num: true, fmt }, { key: 'n', label: 'Months', num: true }, { key: 'same', label: 'Same region' }]);

  // correlation with the US
  const us = MK.filter(c => c !== 'United States').map(c => ({ c, x: corr(R['United States'], R[c], from, to) })).filter(d => d.x).sort((a, b) => b.x.r - a.x.r);
  const top = us[0], low = us[us.length - 1], ind = us.find(d => d.c === 'India'), chn = us.find(d => d.c === 'China');
  document.getElementById('c-cus-h').textContent = top ? `${top.c} tracks the US most closely (${fmt(top.x.r)}); ${low.c} least (${fmt(low.x.r)})` : 'Which markets follow Wall Street?';
  document.getElementById('c-cus-sub').textContent = `Correlation with the S&P 500, monthly returns, ${lab.toLowerCase()}, ${curTxt}` + (ind && chn ? ` · India ${fmt(ind.x.r)}, China ${fmt(chn.x.r)}` : '');
  const d2 = us.slice();
  if (uInst) uInst.dispose();
  uInst = ATLAS.chart('c-cus', {
    grid: { top: 8, right: 44, bottom: 8 },
    tooltip: { formatter: p => { const d = d2[p.dataIndex]; return `<b>${d.c}</b> vs United States<br>Correlation <b>${fmt(d.x.r)}</b> over ${d.x.n} months`; } },
    xAxis: { type: 'value', min: 0, max: 1 },
    yAxis: { type: 'category', inverse: true, data: d2.map(d => d.c), axisLabel: { fontSize: 12 } },
    series: [{ type: 'bar', barMaxWidth: 14, data: d2.map(d => ({ value: +d.x.r.toFixed(3), itemStyle: { color: d.c === 'India' ? ACC : P[['Americas', 'Europe', 'Middle East & Africa', 'Asia-Pacific'].indexOf(regionOf[d.c])] } })),
      label: { show: true, position: 'right', fontSize: 11, formatter: p => fmt(p.value) } }],
  });
  usTbl(us.map(d => ({ c: d.c, region: regionOf[d.c], r: d.x.r, n: d.x.n })),
    [{ key: 'c', label: 'Market' }, { key: 'region', label: 'Region' }, { key: 'r', label: 'Correlation with US', num: true, fmt }, { key: 'n', label: 'Months', num: true }]);
  return { avg, inReg: mean(inReg), cross: mean(cross), top: pairs[0], bottom: pairs[pairs.length - 1], ind, chn };
}

// rolling 3-year average correlation (US dollars), one point per quarter-end month
function rolling() {
  const out = [];
  for (let m = '1993-12'; m <= LAST; m = shift(m, 3)) {
    const from = shift(m, -35); let s = 0, n = 0;
    for (let i = 0; i < MK.length; i++) for (let j = i + 1; j < MK.length; j++) {
      const c = corr(RET.usd[MK[i]], RET.usd[MK[j]], from, m); if (c && c.n >= 30) { s += c.r; n++; }
    }
    if (n >= 20) out.push({ m, r: s / n, pairs: n });
  }
  return out;
}
const RR = rolling();
const peak = RR.slice().sort((a, b) => b.r - a.r)[0], lowR = RR.slice().sort((a, b) => a.r - b.r)[0], now = RR[RR.length - 1];
document.getElementById('c-croll-h').textContent = `Markets moved most in step around ${peak.m.slice(0, 4)} (${fmt(peak.r)}); least around ${lowR.m.slice(0, 4)} (${fmt(lowR.r)}). Today: ${fmt(now.r)}`;
ATLAS.chart('c-croll', {
  grid: { top: 16, right: 16, bottom: 8 },
  tooltip: { trigger: 'axis', formatter: ps => `<b>3 years to ${ps[0].value[0].slice(0, 7)}</b><br>Average correlation <b>${fmt(ps[0].value[1])}</b><br>${RR[ps[0].dataIndex].pairs} market pairs` },
  xAxis: { type: 'time', axisLabel: { formatter: '{yyyy}' } },
  yAxis: { type: 'value', min: 0, max: 1 },
  series: [{ type: 'line', showSymbol: false, data: RR.map(d => [d.m + '-15', +d.r.toFixed(3)]), lineStyle: { width: 2.5 }, itemStyle: { color: P[0] }, areaStyle: { opacity: 0.08 },
    markArea: { silent: true, itemStyle: { color: ATLAS.css('--surface-2') }, label: { color: TXT2, fontSize: 10 },
      data: [[{ name: 'Global financial crisis', xAxis: '2008-09-01' }, { xAxis: '2011-09-30' }], [{ name: 'Covid', xAxis: '2020-02-01' }, { xAxis: '2023-02-28' }]] } }],
});
rollTbl(RR.slice().reverse().map(d => ({ m: '3 years to ' + d.m, r: d.r, n: d.pairs })),
  [{ key: 'm', label: 'Window' }, { key: 'r', label: 'Average correlation', num: true, fmt }, { key: 'n', label: 'Pairs', num: true }]);

const S = draw();
// notes from the default view (last 10 years, US$), computed so they stay true after a data update
ATLAS.notes('n-corr', { items: [
  `<b>Neighbours move together.</b> Over the last 10 years the most closely linked pair is ${S.top.a} and ${S.top.b} (${fmt(S.top.r)}). Markets in the same region average ${fmt(S.inReg)}, against ${fmt(S.cross)} across regions.`,
  S.chn && S.ind && `<b>China is the great diversifier.</b> Its correlation with the US is only ${fmt(S.chn.x.r)}, because foreign money in Chinese shares is limited and its market is driven by local savers and policy. India sits at ${fmt(S.ind.x.r)}.`,
  `<b>Diversification fails when you need it most.</b> The rolling average jumps in crises (2008, 2020) when everything is sold at once. The peak was ${fmt(peak.r)} in the 3 years to ${peak.m}.`,
  '<b>Caveat:</b> correlation measures whether markets move in the same direction in the same month, not whether they grow at the same pace. Two markets can be highly correlated while one triples and the other stays flat. Use the US-dollar view for cross-country comparison: in local currency, exchange-rate moves are hidden.',
].filter(Boolean) });
})();
