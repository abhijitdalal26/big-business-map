/* Browsable study pack for the Business World in Numbers data study.
 *
 * The content is loaded from data.js, which the analysis engine writes on
 * every build.  No framework, no build step: open output/index.html.
 */
(function () {
  "use strict";

  var D = window.STUDY_PACK || {};
  var SECTIONS = D.sections || [];
  var state = { q: "", view: "sections" };

  /* ---------------------------------------------------------------- utils */

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = String(text);
    return n;
  }

  function slug(text) {
    return String(text).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  }

  function haystack(text) {
    return String(text || "").toLowerCase();
  }

  function numeric(value) {
    var cleaned = String(value).replace(/[$,%\s]/g, "").replace(/,/g, "");
    if (cleaned === "" || cleaned === "—") return null;
    var n = parseFloat(cleaned);
    return isNaN(n) ? null : n;
  }

  function compare(a, b) {
    var na = numeric(a);
    var nb = numeric(b);
    if (na !== null && nb !== null) return na - nb;
    return String(a).localeCompare(String(b), undefined, { numeric: true });
  }

  function matches(hay, q) {
    return !q || hay.indexOf(q) !== -1;
  }

  /* The text of a section, minus the numbers sitting behind each chart.
   * Those panels are opt-in, and letting them match would make every
   * search look as though it had hit everything. */
  function sectionHaystack(section) {
    var text = section.textContent;
    var panels = section.querySelectorAll(".chartdata");
    for (var i = 0; i < panels.length; i += 1) {
      text = text.split(panels[i].textContent).join(" ");
    }
    return haystack(text);
  }

  /* Money the way the charts write it: $52.9B, $1.2T, $450M.  Raw dollars
   * in, compact string out; nothing known gives an em dash. */
  function usd(value) {
    if (value === null || value === undefined || value === "") return "—";
    var n = Number(value);
    if (isNaN(n)) return "—";
    var abs = Math.abs(n);
    if (abs >= 1e12) return "$" + trimZero(n / 1e12) + "T";
    if (abs >= 1e9) return "$" + trimZero(n / 1e9) + "B";
    if (abs >= 1e6) return "$" + trimZero(n / 1e6) + "M";
    if (abs >= 1e3) return "$" + trimZero(n / 1e3) + "K";
    return "$" + Math.round(n).toLocaleString();
  }

  /* One decimal, but never a pointless ".0". */
  function trimZero(n) {
    var s = n.toFixed(1);
    return s.slice(-2) === ".0" ? s.slice(0, -2) : s;
  }

  /* A number, or null when the field is empty. */
  function numValue(value) {
    if (value === null || value === undefined || value === "") return null;
    var n = Number(value);
    return isNaN(n) ? null : n;
  }

  /* -------------------------------------------------------------- masthead */

  function renderMasthead() {
    document.title = D.title || "Business World in Numbers";
    var eyebrow = document.getElementById("eyebrow");
    if (D.eyebrow) eyebrow.textContent = D.eyebrow;
    document.getElementById("title").textContent = D.title || "";
    document.getElementById("dek").textContent = D.subtitle || "";

    var bar = document.getElementById("statbar");
    bar.innerHTML = "";
    (D.universe || []).forEach(function (item) {
      var s = el("div", "stat");
      s.appendChild(el("b", null, item.value));
      s.appendChild(el("span", null, item.label));
      bar.appendChild(s);
    });
  }

  function renderNav() {
    var nav = document.getElementById("nav");
    nav.innerHTML = "";
    SECTIONS.forEach(function (sec, i) {
      var a = el("a", null, (i + 1) + ". " + shortTitle(sec.title));
      a.href = "#" + sec.id;
      a.dataset.target = sec.id;
      a.addEventListener("click", function () {
        if (state.view !== "sections") { state.view = "sections"; render(); }
      });
      nav.appendChild(a);
    });
    var a = el("a", null, "Appendix");
    a.href = "#appendix";
    a.dataset.target = "appendix";
    nav.appendChild(a);
  }

  function shortTitle(title) {
    var t = String(title).split(":")[0];
    return t.length < 26 ? t : t.slice(0, 24) + "…";
  }

  /* --------------------------------------------------------------- tables */

  function renderTable(spec) {
    var wrap = el("div", "tablewrap");
    var table = el("table");
    // An optional caption sits on top of the table, inside the card.
    if (spec.caption) table.appendChild(el("caption", null, spec.caption));
    var thead = el("thead");
    var hrow = el("tr");

    spec.columns.forEach(function (name, ci) {
      var th = el("th", null, name);
      th.dataset.col = String(ci);
      var arrow = el("span", "arrow", "↕");
      th.appendChild(arrow);
      th.addEventListener("click", function () { sortTable(table, ci, th); });
      hrow.appendChild(th);
    });
    thead.appendChild(hrow);
    table.appendChild(thead);

    var tbody = el("tbody");
    spec.rows.forEach(function (row) {
      var tr = el("tr");
      row.forEach(function (cell) {
        var text = cell === null || cell === undefined ? "" : String(cell);
        var td = el("td");
        // A cell that points at a CSV becomes a link, so the appendix table
        // index is clickable straight from the page.
        if (/\.csv$/i.test(text.trim()) && text.indexOf("/") !== -1) {
          var a = el("a", null, text);
          a.href = text;
          td.appendChild(a);
        } else {
          td.textContent = text;
        }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    wrap.appendChild(table);

    var meta = el("div", "table-meta");
    var note = spec.total_rows > spec.rows.length
      ? "Showing " + spec.rows.length.toLocaleString() + " of " +
        spec.total_rows.toLocaleString() + " rows"
      : spec.rows.length.toLocaleString() + " rows";
    meta.appendChild(el("span", null, note));
    if (spec.csv) {
      var link = el("a", null, "Download full CSV");
      link.href = spec.csv;
      meta.appendChild(link);
    }
    return { wrap: wrap, meta: meta };
  }

  function sortTable(table, colIndex, th) {
    var tbody = table.tBodies[0];
    var rows = Array.prototype.slice.call(tbody.rows);
    var ascending = !(th.dataset.dir === "asc");
    rows.sort(function (a, b) {
      var av = sortValue(a.cells[colIndex]);
      var bv = sortValue(b.cells[colIndex]);
      return ascending ? compare(av, bv) : compare(bv, av);
    });
    rows.forEach(function (r) { tbody.appendChild(r); });

    markSorted(table, th, ascending ? "asc" : "desc");
  }

  /* Cells may carry the value they should sort by, which is not always the
   * text on screen: "$1.2T" has to sort above "$52.9B". */
  function sortValue(cell) {
    if (!cell) return "";
    if (cell.dataset && cell.dataset.sortValue !== undefined) {
      return cell.dataset.sortValue;
    }
    return cell.textContent;
  }

  /* Point the arrows at one column. */
  function markSorted(table, th, dir) {
    var all = table.tHead.rows[0].cells;
    for (var i = 0; i < all.length; i++) {
      all[i].classList.remove("sorted");
      var a = all[i].querySelector(".arrow");
      if (a) a.textContent = "↕";
    }
    th.classList.add("sorted");
    var arrow = th.querySelector(".arrow");
    if (arrow) arrow.textContent = dir === "asc" ? "↑" : "↓";
    th.dataset.dir = dir;
  }

  /* --------------------------------------------------------------- charts */

  var chartSeq = 0;

  /* One chart is a full-width block: the card, and - when the chart was
   * drawn from a table - the numbers behind it, folded away until asked for.
   * The card keeps its click-to-open-lightbox behaviour; the toggle and the
   * table sit outside the card so neither of them opens the lightbox. */
  function renderChart(chart) {
    var block = el("div", "chartblock");

    var fig = el("figure", "chart");
    var img = el("img");
    img.src = chart.src;
    img.alt = chart.title + " — " + (chart.subtitle || "");
    img.loading = "lazy";
    fig.appendChild(img);
    var cap = el("figcaption");
    cap.appendChild(el("b", null, chart.title));
    cap.appendChild(document.createTextNode(chart.subtitle || ""));
    fig.appendChild(cap);
    fig.addEventListener("click", function () { openLightbox(chart); });
    block.appendChild(fig);

    if (chart.data && chart.data.columns && chart.data.columns.length &&
        chart.data.rows && chart.data.rows.length) {
      var panelId = "chartdata-" + (++chartSeq);
      var toggle = el("button", "chart-toggle", "Show the numbers");
      toggle.type = "button";
      toggle.setAttribute("aria-expanded", "false");
      toggle.setAttribute("aria-controls", panelId);
      block.appendChild(toggle);

      var panel = el("div", "chartdata");
      panel.id = panelId;
      panel.hidden = true;
      // The same table helper the section tables use, so the styling and the
      // click-to-sort behave the same way.
      var built = renderTable({
        caption: chart.data.title || "The numbers behind this chart",
        columns: chart.data.columns,
        rows: chart.data.rows,
        csv: chart.data.csv,
        total_rows: chart.data.total_rows
      });
      panel.appendChild(built.wrap);
      panel.appendChild(built.meta);
      block.appendChild(panel);

      toggle.addEventListener("click", function () {
        var open = panel.hidden;
        panel.hidden = !open;
        toggle.textContent = open ? "Hide the numbers" : "Show the numbers";
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
      });
    }
    return block;
  }

  function openLightbox(chart) {
    var box = document.getElementById("lightbox");
    document.getElementById("lightboxImg").src = chart.src;
    document.getElementById("lightboxImg").alt = chart.title;
    document.getElementById("lightboxCaption").textContent =
      chart.title + (chart.subtitle ? " — " + chart.subtitle : "");
    box.hidden = false;
  }

  function closeLightbox() {
    document.getElementById("lightbox").hidden = true;
  }

  /* ------------------------------------------------------------- sections */

  function renderSection(sec, index) {
    var section = el("section", "section");
    section.id = sec.id;

    var h = el("h2");
    h.appendChild(el("span", "num", String(index + 1).padStart(2, "0")));
    h.appendChild(document.createTextNode(sec.title));
    section.appendChild(h);
    section.appendChild(el("p", "lead", sec.lead));

    if (sec.kv && sec.kv.length) {
      section.appendChild(el("h3", "sub", "Key numbers"));
      var kv = el("div", "kv");
      sec.kv.forEach(function (item) {
        var tile = el("div", "tile");
        tile.appendChild(el("b", null, item.value));
        tile.appendChild(el("span", null, item.label));
        kv.appendChild(tile);
      });
      section.appendChild(kv);
    }

    if (sec.insights && sec.insights.length) {
      section.appendChild(el("h3", "sub", "What the data shows"));
      var ul = el("ul", "insights");
      sec.insights.forEach(function (line) {
        var li = el("li");
        li.innerHTML = boldify(line);
        li.dataset.hay = haystack(line);
        ul.appendChild(li);
      });
      section.appendChild(ul);
    }

    if (sec.charts && sec.charts.length) {
      section.appendChild(el("h3", "sub", "Charts"));
      var grid = el("div", "charts");
      sec.charts.forEach(function (c) { grid.appendChild(renderChart(c)); });
      section.appendChild(grid);
    }

    (sec.tables || []).forEach(function (spec) {
      section.appendChild(el("h3", "sub", spec.title));
      var built = renderTable(spec);
      section.appendChild(built.wrap);
      section.appendChild(built.meta);
    });

    // The directory section carries the directory itself: a search box, a
    // sortable table and a card with everything known about one company.
    if (sec.key === "companies" && DIR.ready && !dirRendered) {
      dirRendered = true;
      section.appendChild(el("h3", "sub", "Company directory"));
      section.appendChild(el("p", "lead dirlead",
        "Search the directory by name, country, sector, owner, CEO or ticker. " +
        "Open a company for everything the reconciliation knows about it."));
      section.appendChild(renderDirectoryPanel());
    }

    return section;
  }

  /* Markdown-lite: the insight lines use **bold** markers. */
  function boldify(text) {
    var escaped = String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;");
    return escaped.replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
  }

  /* ------------------------------------------------------------ directory */

  /* The directory holds every company the reconciliation could name, so it
   * gets a panel of its own: a search box, a sortable table, and a card
   * with everything known about one company.  The search string of every
   * company is built once, on load, so a keystroke only ever costs one pass
   * over pre-lowered strings. */

  var DIR_CAP = 100;                 // rows drawn at a time
  var DIR = { ready: false, rows: [], hay: [], lower: [], col: {}, byName: [] };
  var dirState = { q: "", sortKey: "company", sortDir: "asc", open: -1 };
  var dirRendered = false;
  var dirRefs = { panel: null, tbody: null, count: null, detail: null, table: null };

  /* The columns of the results table, in display order. */
  var DIR_COLS = [
    { key: "company", label: "Company" },
    { key: "country", label: "Country" },
    { key: "sector", label: "Sector" },
    { key: "ownership", label: "Ownership" },
    { key: "list_name", label: "List" },
    { key: "revenue_usd", label: "Revenue", money: true },
    { key: "market_cap_usd", label: "Market value", money: true },
    { key: "website", label: "Website" }
  ];

  /* Every field the detail card shows, when the company has it. */
  var DIR_FIELDS = [
    { key: "country", label: "Country" },
    { key: "country_iso3", label: "ISO3" },
    { key: "region", label: "Region" },
    { key: "sector", label: "Sector" },
    { key: "industry_canon", label: "Industry" },
    { key: "ownership", label: "Ownership" },
    { key: "source", label: "Source" },
    { key: "list_name", label: "List" },
    { key: "n_sources", label: "Sources", count: true },
    { key: "confidence", label: "Confidence" },
    { key: "rank_in_source", label: "Rank in source" },
    { key: "revenue_usd", label: "Revenue", money: true },
    { key: "profit_usd", label: "Profit", money: true },
    { key: "market_cap_usd", label: "Market value", money: true },
    { key: "employees", label: "Employees", count: true },
    { key: "ticker", label: "Ticker" },
    { key: "ceo", label: "CEO" },
    { key: "city", label: "City" },
    { key: "state", label: "State" },
    { key: "year_founded", label: "Year founded" },
    { key: "description", label: "Description", wide: true }
  ];

  /* Links out of the detail card; only the ones that exist are drawn. */
  var DIR_LINKS = [
    { key: "website", label: "Website" },
    { key: "wikipedia", label: "Wikipedia" },
    { key: "forbes_page", label: "Forbes profile" }
  ];

  /* The raw value of one field, "" when the company does not have it. */
  function rawAt(row, index) {
    if (!row || index === undefined || index === null || index < 0) return "";
    var v = row[index];
    return v === null || v === undefined ? "" : v;
  }

  /* Index the directory once: column positions, one lowercased search
   * string per company, and the default order by name. */
  function initDirectory() {
    var pack = window.COMPANIES;
    if (!pack || !pack.columns || !pack.columns.length) return false;
    if (!pack.rows || !pack.rows.length) return false;

    var col = {};
    pack.columns.forEach(function (name, i) { col[name] = i; });
    DIR.col = col;
    DIR.rows = pack.rows;

    var n = pack.rows.length;
    var hay = new Array(n);
    var lower = new Array(n);
    for (var i = 0; i < n; i++) {
      var row = pack.rows[i];
      var name = String(rawAt(row, col.company));
      lower[i] = name.toLowerCase();
      hay[i] = [name,
                rawAt(row, col.country),
                rawAt(row, col.sector),
                rawAt(row, col.ownership),
                rawAt(row, col.ceo),
                rawAt(row, col.ticker)].join(" ").toLowerCase();
    }
    DIR.hay = hay;
    DIR.lower = lower;

    var byName = [];
    for (var j = 0; j < n; j++) byName.push(j);
    byName.sort(function (a, b) {
      return DIR.lower[a] < DIR.lower[b] ? -1 : (DIR.lower[a] > DIR.lower[b] ? 1 : 0);
    });
    DIR.byName = byName;
    DIR.ready = true;
    return true;
  }

  /* The panel: search box, count line, results table, detail card. */
  function renderDirectoryPanel() {
    var panel = el("div", "dirpanel");

    var head = el("div", "dirhead");
    var input = el("input", "dirsearch");
    input.type = "search";
    input.id = "dirSearch";
    input.placeholder = "Search a company, country, sector…";
    input.setAttribute("aria-label", "Search the company directory");
    input.setAttribute("autocomplete", "off");
    input.setAttribute("spellcheck", "false");
    input.value = dirState.q;
    var clear = el("button", "dirclear", "Clear");
    clear.type = "button";
    head.appendChild(input);
    head.appendChild(clear);
    panel.appendChild(head);

    var count = el("p", "dircount");
    count.setAttribute("role", "status");
    panel.appendChild(count);

    var wrap = el("div", "tablewrap dirtable");
    var table = el("table");
    var thead = el("thead");
    var hrow = el("tr");
    DIR_COLS.forEach(function (col, ci) {
      var th = el("th", null, col.label);
      th.dataset.col = String(ci);
      th.dataset.key = col.key;
      th.appendChild(el("span", "arrow", "↕"));
      th.addEventListener("click", function () { sortDirectory(col.key, th); });
      hrow.appendChild(th);
    });
    thead.appendChild(hrow);
    table.appendChild(thead);
    var tbody = el("tbody");
    table.appendChild(tbody);
    wrap.appendChild(table);
    panel.appendChild(wrap);

    var detail = el("div", "compdetail");
    detail.hidden = true;
    // Focusable, so the card can take the focus when a company is opened.
    detail.setAttribute("tabindex", "-1");
    panel.appendChild(detail);

    dirRefs.panel = panel;
    dirRefs.tbody = tbody;
    dirRefs.count = count;
    dirRefs.detail = detail;
    dirRefs.table = table;

    input.addEventListener("input", function () {
      dirState.q = input.value;
      filterDirectory();
    });
    clear.addEventListener("click", function () {
      dirState.q = "";
      input.value = "";
      filterDirectory();
      input.focus();
    });

    filterDirectory();
    var th = dirHeader(table, dirState.sortKey);
    if (th) markSorted(table, th, dirState.sortDir);
    if (dirState.open >= 0) renderCompanyDetail(dirState.open);
    return panel;
  }

  /* The header cell of one column. */
  function dirHeader(table, key) {
    var cells = table.tHead.rows[0].cells;
    for (var i = 0; i < cells.length; i++) {
      if (cells[i].dataset.key === key) return cells[i];
    }
    return null;
  }

  /* Click-to-sort on a header cell, like every other table on the page.
   * The order lives in dirState, so it survives a re-render. */
  function sortDirectory(key, th) {
    if (dirState.sortKey === key) {
      dirState.sortDir = dirState.sortDir === "asc" ? "desc" : "asc";
    } else {
      dirState.sortKey = key;
      dirState.sortDir = "asc";
    }
    filterDirectory();
    markSorted(dirRefs.table, th, dirState.sortDir);
  }

  /* The query that filters the directory: the panel's own search box wins,
   * the masthead search is the fallback. */
  function dirQuery() {
    var own = dirState.q.trim().toLowerCase();
    if (own) return own;
    return haystack(state.q).trim();
  }

  /* Filter, sort, draw at most DIR_CAP rows, and say what was left out. */
  function filterDirectory() {
    if (!DIR.ready || !dirRefs.tbody) return;
    var q = dirQuery();
    var matches = [];
    var i;

    if (dirState.sortKey === "company") {
      // The default order is by name and is ready-made, so no sorting here.
      for (i = 0; i < DIR.byName.length; i++) {
        var bi = DIR.byName[i];
        if (!q || DIR.hay[bi].indexOf(q) !== -1) matches.push(bi);
      }
      if (dirState.sortDir === "desc") matches.reverse();
    } else {
      for (i = 0; i < DIR.rows.length; i++) {
        if (!q || DIR.hay[i].indexOf(q) !== -1) matches.push(i);
      }
      sortMatches(matches, dirState.sortKey, dirState.sortDir);
    }

    var tbody = dirRefs.tbody;
    tbody.innerHTML = "";
    var shown = Math.min(matches.length, DIR_CAP);
    for (var m = 0; m < shown; m++) {
      tbody.appendChild(dirRow(matches[m]));
    }

    var total = DIR.rows.length;
    var line;
    if (!q) {
      line = "Showing all " + total.toLocaleString() + " companies";
    } else if (!matches.length) {
      line = "No company matches “" + q + "”";
    } else {
      line = matches.length.toLocaleString() + " of " + total.toLocaleString() +
        " companies match";
    }
    if (matches.length > DIR_CAP) {
      line += " — showing the first " + DIR_CAP;
    }
    if (!dirState.q.trim() && state.q.trim()) {
      line += " (filtered by the search above)";
    }
    dirRefs.count.textContent = line;
    if (dirRefs.panel) dirRefs.panel.dataset.hits = String(matches.length);
  }

  /* Sort the matched companies by one column. */
  function sortMatches(list, key, dir) {
    var col = DIR.col[key];
    var money = key === "revenue_usd" || key === "market_cap_usd";
    var sign = dir === "desc" ? -1 : 1;
    list.sort(function (a, b) {
      var av = rawAt(DIR.rows[a], col);
      var bv = rawAt(DIR.rows[b], col);
      if (money) {
        var na = numValue(av);
        var nb = numValue(bv);
        if (na === null && nb === null) return 0;
        if (na === null) return 1;      // unknowns last
        if (nb === null) return -1;
        return sign * (na - nb);
      }
      var la = String(av).toLowerCase();
      var lb = String(bv).toLowerCase();
      if (la < lb) return -sign;
      if (la > lb) return sign;
      return 0;
    });
  }

  /* One row of the results table.  The name is a real button, so the row is
   * reachable from the keyboard as well as from the mouse. */
  function dirRow(index) {
    var row = DIR.rows[index];
    var tr = el("tr", "dirrow");
    tr.addEventListener("click", function () { openCompany(index); });

    var nameCell = el("td");
    var name = el("button", "compname", String(rawAt(row, DIR.col.company)));
    name.type = "button";
    nameCell.appendChild(name);
    nameCell.dataset.sortValue = String(rawAt(row, DIR.col.company));
    tr.appendChild(nameCell);

    DIR_COLS.slice(1).forEach(function (col) {
      var value = rawAt(row, DIR.col[col.key]);
      var cell = el("td");
      if (col.key === "website") {
        var url = String(value).trim();
        if (url) {
          var link = el("a", null, "Visit");
          link.href = url;
          link.target = "_blank";
          link.rel = "noopener noreferrer";
          // The link opens the site, not the company card.
          link.addEventListener("click", function (e) { e.stopPropagation(); });
          cell.appendChild(link);
        } else {
          cell.textContent = "—";
        }
        cell.dataset.sortValue = url;
      } else if (col.money) {
        cell.textContent = usd(value);
        cell.dataset.sortValue = value === "" ? "" : String(value);
      } else {
        cell.textContent = value === "" ? "—" : String(value);
        cell.dataset.sortValue = String(value);
      }
      tr.appendChild(cell);
    });
    return tr;
  }

  /* Open the card with everything known about one company. */
  function openCompany(index) {
    dirState.open = index;
    renderCompanyDetail(index);
    // Move the focus to the card, so the keyboard follows the reader there.
    if (dirRefs.detail && dirRefs.detail.focus) dirRefs.detail.focus();
  }

  function renderCompanyDetail(index) {
    var row = DIR.rows[index];
    var panel = dirRefs.detail;
    if (!row || !panel) return;
    panel.innerHTML = "";

    var head = el("div", "compdetail-head");
    head.appendChild(el("h4", null, String(rawAt(row, DIR.col.company))));
    var close = el("button", "compdetail-close", "×");
    close.type = "button";
    close.setAttribute("aria-label", "Close the company details");
    close.addEventListener("click", function () {
      dirState.open = -1;
      panel.hidden = true;
    });
    head.appendChild(close);
    panel.appendChild(head);

    var fields = el("dl", "compfields");
    DIR_FIELDS.forEach(function (field) {
      var value = rawAt(row, DIR.col[field.key]);
      if (value === "" || value === null) return;
      var dt = el("dt", field.wide ? "wide" : null, field.label);
      var dd = el("dd", field.wide ? "wide" : null);
      if (field.money) {
        dd.textContent = usd(value);
        dd.title = "$" + Number(value).toLocaleString();
      } else if (field.count) {
        dd.textContent = Number(value).toLocaleString();
      } else {
        dd.textContent = String(value);
      }
      fields.appendChild(dt);
      fields.appendChild(dd);
    });
    panel.appendChild(fields);

    var links = el("p", "complinks");
    var any = false;
    DIR_LINKS.forEach(function (pair) {
      var url = String(rawAt(row, DIR.col[pair.key])).trim();
      if (!url) return;
      any = true;
      var link = el("a", null, pair.label);
      link.href = url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      links.appendChild(link);
    });
    if (any) panel.appendChild(links);

    panel.hidden = false;
  }

  /* ------------------------------------------------------------- appendix */

  function renderAppendix() {
    var appendix = el("section", "section");
    appendix.id = "appendix";
    appendix.appendChild(el("h2", null, "Appendix: sources, charts, tables and caveats"));

    var ap = D.appendix || {};
    if (ap.datasets && ap.datasets.rows.length) {
      appendix.appendChild(el("h3", "sub", "A — the datasets behind every number"));
      appendix.appendChild(renderTable(ap.datasets).wrap);
    }
    if (ap.charts && ap.charts.rows.length) {
      appendix.appendChild(el("h3", "sub", "B — chart index"));
      appendix.appendChild(renderTable(ap.charts).wrap);
    }
    if (ap.tables && ap.tables.rows.length) {
      appendix.appendChild(el("h3", "sub", "C — table index"));
      appendix.appendChild(renderTable(ap.tables).wrap);
    }
    if (ap.caveats && ap.caveats.length) {
      appendix.appendChild(el("h3", "sub", "D — caveats"));
      var card = el("div", "card");
      var ul = el("ul", "insights");
      ap.caveats.forEach(function (c) {
        var li = el("li");
        li.innerHTML = boldify(c);
        ul.appendChild(li);
      });
      card.appendChild(ul);
      appendix.appendChild(card);
    }
    return appendix;
  }

  /* ------------------------------------------------------------ all charts */

  function renderAllCharts() {
    var wrap = el("section", "section");
    wrap.id = "all-charts";
    wrap.appendChild(el("h2", null, "Every chart, in one place"));
    wrap.appendChild(el("p", "lead",
      "All charts produced by the analysis engine, grouped by the section " +
      "they belong to. Click any chart to see it full size."));

    SECTIONS.forEach(function (sec) {
      if (!sec.charts || !sec.charts.length) return;
      wrap.appendChild(el("h3", "sub", sec.title));
      var grid = el("div", "charts");
      sec.charts.forEach(function (c) { grid.appendChild(renderChart(c)); });
      wrap.appendChild(grid);
    });
    return wrap;
  }

  /* --------------------------------------------------------------- render */

  function render() {
    var content = document.getElementById("content");
    content.innerHTML = "";
    // The panel is rebuilt with the page; the search box, the order and the
    // open company live in dirState and are put back by the new panel.
    dirRendered = false;
    dirRefs.panel = null;
    dirRefs.tbody = null;
    dirRefs.count = null;
    dirRefs.detail = null;
    dirRefs.table = null;
    if (state.view === "charts") {
      content.appendChild(renderAllCharts());
    } else {
      if (D.note) content.appendChild(el("div", "callout", D.note));
      SECTIONS.forEach(function (sec, i) { content.appendChild(renderSection(sec, i)); });
      content.appendChild(renderAppendix());
    }
    applyFilters();
    updateStatus();
    var toggle = document.getElementById("viewToggle");
    toggle.textContent = state.view === "charts" ? "Back to sections" : "All charts";
    toggle.setAttribute("aria-pressed", state.view === "charts" ? "true" : "false");
  }

  function applyFilters() {
    var q = haystack(state.q).trim();
    // The directory follows the masthead search when it has no search of its
    // own, so a company name typed up there finds the company.
    if (DIR.ready && dirRefs.panel) filterDirectory();
    document.querySelectorAll(".section").forEach(function (section) {
      if (state.view === "charts") {
        section.hidden = false;
        return;
      }
      var hits = [];
      section.querySelectorAll("li[data-hay]").forEach(function (li) {
        var ok = matches(li.dataset.hay, q);
        li.hidden = !ok;
        if (ok) hits.push(true);
      });
      // Directory rows keep their own filter, and the numbers behind a chart
      // are opt-in: neither should be swept up by the masthead search.
      var shownRows = 0;
      section.querySelectorAll("tbody tr").forEach(function (tr) {
        if (tr.classList.contains("dirrow")) return;
        if (tr.closest(".chartdata")) return;
        var ok = !q || haystack(tr.textContent).indexOf(q) !== -1;
        tr.hidden = !ok;
        if (ok) shownRows += 1;
      });
      var visible = hits.length > 0 || !q;
      if (q) {
        var body = sectionHaystack(section);
        // A section with a directory also counts the companies it holds.
        var dirHits = dirHitCount(section);
        visible = (body.indexOf(q) !== -1 || dirHits > 0) && (
          section.querySelectorAll("li[data-hay]:not([hidden])").length > 0 ||
          shownRows > 0 ||
          section.querySelectorAll(".chart").length > 0 ||
          dirHits > 0);
      }
      section.hidden = !visible;
    });
  }

  /* How many companies the directory currently holds for this section. */
  function dirHitCount(section) {
    if (!DIR.ready || !dirRefs.panel) return 0;
    if (!section.querySelector(".dirpanel")) return 0;
    var hits = Number(dirRefs.panel.dataset.hits || 0);
    return isNaN(hits) ? 0 : hits;
  }

  function updateStatus() {
    var status = document.getElementById("status");
    if (state.view === "charts") {
      status.textContent = "Showing every chart. Use the button above to go back.";
      return;
    }
    var q = state.q.trim();
    if (!q) {
      status.textContent = SECTIONS.length + " sections · " +
        (D.chart_count || 0) + " charts · " + (D.table_count || 0) + " tables.";
      return;
    }
    var shown = document.querySelectorAll(".section:not([hidden])").length;
    status.textContent = shown + " of " + SECTIONS.length +
      " sections match “" + q + "”.";
  }

  /* ---------------------------------------------------------------- wiring */

  function init() {
    renderMasthead();
    renderNav();
    // The company directory is indexed once, before the page is drawn.  When
    // companies.js is missing the panel is simply not drawn.
    initDirectory();
    render();

    document.getElementById("search").addEventListener("input", function (e) {
      state.q = e.target.value;
      if (state.view === "charts") { state.view = "sections"; render(); }
      else { applyFilters(); updateStatus(); }
    });

    document.getElementById("viewToggle").addEventListener("click", function () {
      state.view = state.view === "charts" ? "sections" : "charts";
      render();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });

    document.getElementById("lightboxClose").addEventListener("click", closeLightbox);
    document.getElementById("lightbox").addEventListener("click", function (e) {
      if (e.target === e.currentTarget) closeLightbox();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeLightbox();
    });

    var footer = document.getElementById("footer");
    footer.appendChild(el("p", null,
      "Generated by data_analysis/build_report.py on " + (D.generated || "—") +
      ". Every number traces to a CSV in data/; every chart is in charts/. " +
      "This is the analysis layer — the article is written separately."));

    // highlight the nav entry for the section in view
    var links = Array.prototype.slice.call(
      document.querySelectorAll("#nav a"));
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        links.forEach(function (a) {
          a.classList.toggle("active", a.dataset.target === entry.target.id);
        });
      });
    }, { rootMargin: "-10% 0px -75% 0px" });
    document.querySelectorAll(".section").forEach(function (s) { observer.observe(s); });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
