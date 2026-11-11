/* Earth Economy — shared helpers. Load AFTER echarts and BEFORE page scripts.
   Data files are plain JS (window.ATLAS.<name> = {...}) so pages work from file:// without a server. */
window.ATLAS = window.ATLAS || {};

(function () {
  const PAGES = [
    ['index.html', 'Overview'],
    ['scale.html', 'Scale'],
    ['geography.html', 'Geography'],
    ['sectors.html', 'Sectors'],
    ['ownership.html', 'Ownership'],
    ['markets.html', 'Stock markets'],
    ['startups.html', 'Startups & AI'],
    ['time.html', 'Change over time'],
    ['context.html', 'Big picture'],
    ['directory.html', 'Company finder'],
    ['notebook.html', "Writer's notebook"],
  ];

  // ---------- theme ----------
  const saved = (() => { try { return localStorage.getItem('atlas-theme'); } catch (e) { return null; } })();
  if (saved) document.documentElement.setAttribute('data-theme', saved);

  function isDark() {
    const t = document.documentElement.getAttribute('data-theme');
    if (t) return t === 'dark';
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }
  function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

  // ---------- nav ----------
  function renderNav() {
    const here = location.pathname.split('/').pop() || 'index.html';
    const bar = document.createElement('div');
    bar.className = 'topbar';
    bar.innerHTML = `<div class="inner">
      <a class="brand" href="index.html">Earth <b>Economy</b></a>
      <div class="nav-wrap"><nav class="nav">${PAGES.map(([h, t]) => `<a href="${h}" class="${h === here ? 'active' : ''}">${t}</a>`).join('')}</nav></div>
      <button class="theme-btn" type="button" title="Toggle theme">${isDark() ? 'Light' : 'Dark'}</button></div>`;
    document.body.prepend(bar);
    // On a phone the nav is a sideways strip: start it at the current page.
    const nav = bar.querySelector('.nav'), act = nav.querySelector('a.active');
    if (act) nav.scrollLeft = act.offsetLeft - (nav.clientWidth - act.offsetWidth) / 2;
    bar.querySelector('.theme-btn').onclick = () => {
      const next = isDark() ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('atlas-theme', next); } catch (e) {}
      location.reload(); // simplest way to re-theme every chart
    };
    const f = document.createElement('footer');
    f.innerHTML = `<div class="wrap">Earth Economy — research pack. Sources: Forbes Global 2000 (2026), Fortune Global 500 (2026),
      CompaniesMarketCap, SEC EDGAR, CB Insights unicorn list, Forbes Cloud 100, World Bank Open Data, and others named under each chart.
      Figures are snapshots; check the "caveat" boxes before quoting.</div>`;
    document.body.append(f);
  }

  // ---------- formatting ----------
  // fmtUSD(value, unit): unit is 'usd' | 'musd' | 'busd' — tells what the raw number is in.
  function fmtUSD(v, unit = 'usd', digits) {
    if (v == null || isNaN(v)) return '—';
    let x = unit === 'musd' ? v * 1e6 : unit === 'busd' ? v * 1e9 : v;
    const a = Math.abs(x);
    const d = digits != null ? digits : (a >= 1e12 ? 1 : a >= 1e9 ? 1 : 0);
    if (a >= 1e12) return '$' + (x / 1e12).toFixed(d) + 'T';
    if (a >= 1e9) return '$' + (x / 1e9).toFixed(d) + 'B';
    if (a >= 1e6) return '$' + (x / 1e6).toFixed(d) + 'M';
    if (a >= 1e3) return '$' + (x / 1e3).toFixed(0) + 'K';
    return '$' + x.toFixed(0);
  }
  function fmtNum(v, d = 0) {
    if (v == null || isNaN(v)) return '—';
    const a = Math.abs(v);
    if (a >= 1e9) return (v / 1e9).toFixed(1) + 'B';
    if (a >= 1e6) return (v / 1e6).toFixed(1) + 'M';
    if (a >= 1e4) return (v / 1e3).toFixed(0) + 'K';
    return v.toLocaleString('en-US', { maximumFractionDigits: d });
  }
  function fmtPct(v, d = 1) { return v == null || isNaN(v) ? '—' : v.toFixed(d) + '%'; }

  // ---------- palette ----------
  function palette() { return ['--s1', '--s2', '--s3', '--s4', '--s5', '--s6', '--s7', '--s8'].map(css); }
  function seq() { return ['--seq-1', '--seq-2', '--seq-3', '--seq-4', '--seq-5'].map(css); }
  function diverging() { return [css('--div-neg'), css('--div-mid'), css('--div-pos')]; }

  // ---------- "what they do" in company tooltips ----------
  // data/ideas.js (built by site/build/ideas.py) maps a normalised company name to a one-line
  // description. Any chart tooltip about a single company gets that line appended, so pages
  // need no code of their own. nameKey() must stay in step with nk() in site/build/ideas.py.
  const LEGAL = new Set(['inc', 'incorporated', 'corp', 'corporation', 'co', 'company', 'ltd', 'limited', 'plc', 'nv',
    'ag', 'sa', 'se', 'spa', 'ab', 'asa', 'oyj', 'as', 'bhd', 'berhad', 'tbk', 'llc', 'lp', 'kgaa', 'gmbh', 'holding',
    'holdings', 'group', 'cos', 'companies']);
  function nameKey(n) {
    let s = String(n).normalize('NFKD').replace(/[^\x00-\x7f]/g, '').toLowerCase().replace(/&/g, ' and ');
    s = s.replace(/['`]/g, '');
    const j = [];
    s.split(/[^a-z0-9]+/).filter(Boolean).forEach(x => {   // glue runs of single letters: U.S. -> us
      if (x.length === 1 && j.length && j[j.length - 1][0] === '\0') j[j.length - 1] += x;
      else j.push(x.length === 1 ? '\0' + x : x);
    });
    let w = j.map(x => x.replace(/^\0/, '')).map(x => (x === 'corp' ? 'corporation' : x));
    if (w.length > 1 && (w[0] === 'the' || w[0] === 'pt')) w = w.slice(1);
    while (w.length > 1 && LEGAL.has(w[w.length - 1])) w = w.slice(0, -1);
    return w.join('');
  }
  function ideaFor(p) {
    const ideas = window.ATLAS_IDEAS;
    if (!ideas || !p || Array.isArray(p)) return null;   // axis tooltips list many series: skip
    const d = p.data, cands = [p.name];
    if (d && typeof d === 'object') {
      cands.push(d.name, d.n, d.company, d.nm, d.label);
      if (Array.isArray(d)) cands.push(...d.slice(0, 4));
      // Some charts tuck the row one level down, e.g. {value: [x, y], r: {company: ...}}.
      Object.values(d).forEach(v => {
        if (v && typeof v === 'object' && !Array.isArray(v)) cands.push(v.company, v.name, v.n, v.nm);
      });
      if (Array.isArray(d.value)) cands.push(...d.value.slice(-3));
    }
    if (Array.isArray(p.value)) cands.push(...p.value.slice(-3));
    for (const c of cands) {
      if (typeof c !== 'string' || c.length < 2) continue;
      const line = ideas[nameKey(c)];
      if (line) return line;
    }
    return null;
  }
  // Fallback for charts whose data holds only numbers or a row index: use the bold title the
  // tooltip itself starts with, e.g. "<b>Amazon</b> (#1)<br>...".
  function ideaFromTitle(html) {
    const m = /^\s*<(b|strong)>(.*?)<\/\1>/i.exec(html);
    if (!m || !window.ATLAS_IDEAS) return null;
    const t = m[2].replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').replace(/\s*[#(·].*$/, '').trim();
    return t.length > 2 ? window.ATLAS_IDEAS[nameKey(t)] || null : null;
  }
  const escHTML = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  function withIdea(fmt) {
    if (typeof fmt !== 'function' || fmt.__idea) return fmt;
    const f = function (p) {
      const out = fmt.apply(this, arguments);
      const line = typeof out === 'string' && !Array.isArray(p) ? ideaFor(p) || ideaFromTitle(out) : null;
      return line ? `${out}<div class="tip-idea"><b>What they do:</b> ${escHTML(line)}</div>` : out;
    };
    f.__idea = true;
    return f;
  }
  function addIdeas(opt) {
    if (!window.ATLAS_IDEAS || !opt || typeof opt !== 'object') return opt;
    const fixTip = t => (t && typeof t.formatter === 'function' ? Object.assign({}, t, { formatter: withIdea(t.formatter) }) : t);
    const fixList = v => (v == null ? v : Array.isArray(v) ? v.map(fixTip) : fixTip(v));
    const o = Object.assign({}, opt);
    if (o.tooltip) o.tooltip = fixList(o.tooltip);
    if (o.series) {
      const fixS = s => (s && s.tooltip ? Object.assign({}, s, { tooltip: fixTip(s.tooltip) }) : s);
      o.series = Array.isArray(o.series) ? o.series.map(fixS) : fixS(o.series);
    }
    return o;
  }

  // ---------- echarts ----------
  // ATLAS.chart(elOrId, option) -> echarts instance, themed, responsive, with hover tooltips on.
  function chart(el, option) {
    if (typeof el === 'string') el = document.getElementById(el);
    const inst = echarts.init(el, null, { renderer: 'canvas' });
    const text = css('--text'), text2 = css('--text-2'), grid = css('--grid'), surf = css('--surface'), border = css('--border');
    const base = {
      color: palette(),
      backgroundColor: 'transparent',
      textStyle: { fontFamily: css('--font') || 'system-ui', color: text2 },
      grid: { left: 8, right: 24, top: 40, bottom: 8, containLabel: true },
      tooltip: {
        trigger: 'item', confine: true,
        backgroundColor: surf, borderColor: border, textStyle: { color: text, fontSize: 13 },
        extraCssText: 'box-shadow:0 4px 16px rgba(0,0,0,.15);border-radius:8px;max-width:340px;white-space:normal;',
      },
      legend: { textStyle: { color: text2 }, top: 0, icon: 'roundRect', itemWidth: 12, itemHeight: 8 },
    };
    const axisDefaults = {
      axisLine: { lineStyle: { color: border } }, axisTick: { show: false },
      axisLabel: { color: text2 }, splitLine: { lineStyle: { color: grid } }, nameTextStyle: { color: text2 },
    };
    const merged = Object.assign({}, base, option);
    merged.tooltip = Object.assign({}, base.tooltip, option.tooltip || {});
    if (option.legend !== false && option.legend) merged.legend = Object.assign({}, base.legend, option.legend);
    if (option.grid) merged.grid = Object.assign({}, base.grid, option.grid);
    ['xAxis', 'yAxis'].forEach(k => {
      if (!option[k]) return;
      const fix = a => Object.assign({}, axisDefaults, a, {
        axisLabel: Object.assign({}, axisDefaults.axisLabel, a.axisLabel || {}),
        splitLine: Object.assign({}, axisDefaults.splitLine, a.splitLine || {}),
      });
      merged[k] = Array.isArray(option[k]) ? option[k].map(fix) : fix(option[k]);
    });
    // Pages also call inst.setOption() later (filters, toggles), so phone tweaks hook in there too.
    const raw = inst.setOption.bind(inst);
    inst.setOption = (opt, ...rest) => { opt = addIdeas(opt); return raw(isPhone() ? mobilize(opt) : opt, ...rest); };
    inst.setOption(merged);
    window.addEventListener('resize', () => inst.resize());
    return inst;
  }

  function isPhone() { return window.matchMedia && window.matchMedia('(max-width: 640px)').matches; }
  const arr = v => (v == null ? [] : Array.isArray(v) ? v : [v]);
  const mapEach = (v, fn) => (v == null ? v : Array.isArray(v) ? v.map(fn) : fn(v));

  // Phone-only chart tweaks: legends scroll instead of wrapping over the plot, long category
  // labels are cut short so bars keep their width, and nothing grabs one-finger page scrolling.
  function mobilize(opt) {
    if (!opt || typeof opt !== 'object') return opt;
    const o = Object.assign({}, opt);
    if (o.legend && o.legend !== false) o.legend = mapEach(o.legend, l => Object.assign({ type: 'scroll' }, l));
    ['xAxis', 'yAxis'].forEach(k => {
      o[k] = mapEach(o[k], a => {
        if (!a || typeof a !== 'object') return a;
        const lab = Object.assign({ fontSize: 11 }, a.axisLabel || {});
        if (a.type === 'category' && k === 'yAxis' && lab.width == null) Object.assign(lab, { width: 96, overflow: 'truncate' });
        if (k === 'xAxis') lab.hideOverlap = true;
        const extra = k === 'xAxis' && a.type === 'value' && a.splitNumber == null ? { splitNumber: 3 } : {};
        return Object.assign({}, a, extra, { axisLabel: lab });
      });
    });
    if (o.dataZoom) o.dataZoom = arr(o.dataZoom).filter(z => z.type !== 'inside');
    if (o.geo) o.geo = mapEach(o.geo, g => Object.assign({}, g, { roam: false }));
    if (o.series) o.series = mapEach(o.series, s => (s && (s.type === 'map' || s.type === 'graph') && s.roam ? Object.assign({}, s, { roam: false }) : s));
    return o;
  }

  // ---------- tables ----------
  // ATLAS.table(container, rows, columns) ; columns: [{key, label, fmt?: fn, num?: bool}]
  // Sortable by clicking headers. Returns {update(rows)}.
  function table(container, rows, columns, opts = {}) {
    if (typeof container === 'string') container = document.getElementById(container);
    let data = rows.slice(), sortKey = null, dir = -1;
    const limit = opts.limit || 500;
    function draw() {
      const shown = data.slice(0, limit);
      container.innerHTML = `<div class="tbl-wrap"><table class="data"><thead><tr>${columns.map(c =>
        `<th class="${c.num ? 'n' : ''}" data-k="${c.key}">${c.label}${sortKey === c.key ? (dir < 0 ? ' ▾' : ' ▴') : ''}</th>`).join('')}</tr></thead>
        <tbody>${shown.map(r => `<tr>${columns.map(c => `<td class="${c.num ? 'n' : ''}">${c.fmt ? c.fmt(r[c.key], r) : (r[c.key] ?? '—')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
        ${data.length > limit ? `<p class="src">Showing ${limit} of ${data.length.toLocaleString()} rows.</p>` : ''}`;
      container.querySelectorAll('th').forEach(th => th.onclick = () => {
        const k = th.dataset.k; dir = sortKey === k ? -dir : -1; sortKey = k;
        data.sort((a, b) => { const x = a[k], y = b[k]; if (x == null) return 1; if (y == null) return -1;
          return (typeof x === 'number' ? x - y : String(x).localeCompare(String(y))) * dir; });
        draw();
      });
    }
    draw();
    return { update(r) { data = r.slice(); draw(); } };
  }

  // ATLAS.tableToggle(buttonId, containerId, rows, columns): a "Show data table" link under a chart (accessibility + checking numbers)
  function tableToggle(btn, box, rows, columns) {
    btn = typeof btn === 'string' ? document.getElementById(btn) : btn;
    box = typeof box === 'string' ? document.getElementById(box) : box;
    box.hidden = true; let built = false;
    btn.textContent = 'Show data table';
    btn.onclick = () => { if (!built) { table(box, rows, columns); built = true; } box.hidden = !box.hidden; btn.textContent = box.hidden ? 'Show data table' : 'Hide data table'; };
  }

  // ATLAS.notes(containerId, {title, items:[html], caveat?:bool})
  function notes(el, { title = "Writer's notes", items = [], caveat = false }) {
    if (typeof el === 'string') el = document.getElementById(el);
    el.className = 'notes' + (caveat ? ' caveat' : '');
    el.innerHTML = `<h4>${title}</h4><ul>${items.map(i => `<li>${i}</li>`).join('')}</ul>`;
  }

  // ATLAS.tiles(containerId, [{v, l, s}])
  function tiles(el, list) {
    if (typeof el === 'string') el = document.getElementById(el);
    el.className = 'tiles';
    el.innerHTML = list.map(t => `<div class="tile"><div class="v">${t.v}</div><div class="l">${t.l}</div>${t.s ? `<div class="s">${t.s}</div>` : ''}</div>`).join('');
  }

  Object.assign(window.ATLAS, { chart, nameKey, ideaFor, table, tableToggle, notes, tiles, fmtUSD, fmtNum, fmtPct, palette, seq, diverging, css, isDark, PAGES });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', renderNav); else renderNav();
})();
