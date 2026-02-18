const state = {
  species_id: null, vendor_id: null, category_id: null,
  format_id: null, max_price: null,
  sort: 'price', order: 'asc', page: 1,
};
const labels = {};

// Track which product_id is currently expanded (null = none)
let expandedProductId = null;

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function setHasValue(id, val) {
  const el = document.getElementById(id);
  if (el) el.classList.toggle('has-value', !!val);
}

function onFilterChange(key) {
  const ids = { species:'f-species', vendor:'f-vendor', category:'f-category', format:'f-format' };
  const sel = document.getElementById(ids[key]);
  const val = sel.value ? parseInt(sel.value) : null;
  state[key + '_id'] = val;
  state.page = 1;
  setHasValue(ids[key], val);
  if (val) labels[key] = sel.options[sel.selectedIndex].text.replace(/ [(][0-9]+[)]$/, '');
  else     delete labels[key];
  if (key === 'category') {
    state.format_id = null;
    delete labels.format;
    const ff = document.getElementById('f-format');
    if (ff) { ff.value = ''; setHasValue('f-format', false); }
    document.getElementById('format-group').style.display = val ? 'flex' : 'none';
  }
  closeDetail();
  fetchAndRender();
}

let priceTimer = null;
function onPriceInput() {
  clearTimeout(priceTimer);
  priceTimer = setTimeout(() => {
    const val = document.getElementById('f-price').value;
    state.max_price = val ? parseFloat(val) : null;
    state.page = 1;
    setHasValue('f-price', state.max_price);
    if (state.max_price) labels.price = '<= ' + Math.round(state.max_price) + ' SEK';
    else delete labels.price;
    closeDetail();
    fetchAndRender();
  }, 400);
}

function sortBy(col) {
  state.order = (state.sort === col && state.order === 'asc') ? 'desc' : 'asc';
  state.sort = col;
  state.page = 1;
  closeDetail();
  fetchAndRender();
}

function goToPage(p) {
  state.page = p;
  closeDetail();
  fetchAndRender();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function clearFilter(key) {
  const ids = { species:'f-species', vendor:'f-vendor', category:'f-category', format:'f-format', price:'f-price' };
  if (key === 'price') state.max_price = null;
  else state[key + '_id'] = null;
  delete labels[key];
  const el = document.getElementById(ids[key]);
  if (el) { el.value = ''; setHasValue(ids[key], false); }
  if (key === 'category') {
    state.format_id = null; delete labels.format;
    const ff = document.getElementById('f-format');
    if (ff) { ff.value = ''; setHasValue('f-format', false); }
    document.getElementById('format-group').style.display = 'none';
  }
  state.page = 1;
  closeDetail();
  fetchAndRender();
}

function clearAll() {
  ['species','vendor','category','format'].forEach(k => {
    state[k+'_id'] = null;
    const el = document.getElementById('f-'+k);
    if (el) { el.value=''; setHasValue('f-'+k, false); }
  });
  state.max_price = null;
  const fp = document.getElementById('f-price');
  if (fp) { fp.value=''; setHasValue('f-price', false); }
  document.getElementById('format-group').style.display = 'none';
  Object.keys(labels).forEach(k => delete labels[k]);
  state.page = 1;
  closeDetail();
  fetchAndRender();
}

function renderChips() {
  const row = document.getElementById('chips-row');
  const active = Object.entries(labels);
  if (!active.length) { row.innerHTML = ''; return; }
  let html = active.map(([k,l]) =>
    `<span class="chip">${esc(l)}<span class="chip-x" onclick="clearFilter('${k}')">x</span></span>`
  ).join('');
  if (active.length > 1) html += `<button class="chips-clear" onclick="clearAll()">Clear all</button>`;
  row.innerHTML = html;
}

function updateSortHeaders() {
  document.querySelectorAll('thead th[data-col]').forEach(th => {
    const col = th.dataset.col;
    const base = col.charAt(0).toUpperCase() + col.slice(1);
    if (state.sort === col) {
      th.classList.add('sorted');
      th.textContent = base + (state.order === 'asc' ? ' ^' : ' v');
    } else {
      th.classList.remove('sorted');
      th.textContent = base;
    }
  });
}

/* ===================== INLINE DETAIL ===================== */

function closeDetail() {
  if (expandedProductId === null) return;
  expandedProductId = null;
  document.querySelectorAll('tr.detail-expand-row').forEach(r => r.remove());
  document.querySelectorAll('tr.data-row.active-row').forEach(r => r.classList.remove('active-row'));
}

function toggleDetail(productId, sourceRow) {
  if (expandedProductId === productId) { closeDetail(); return; }
  closeDetail();
  expandedProductId = productId;
  sourceRow.classList.add('active-row');

  const detailTr = document.createElement('tr');
  detailTr.className = 'detail-expand-row';
  detailTr.innerHTML =
    `<td colspan="8" class="detail-expand-cell">
       <div class="detail-expand-inner" id="detail-inner-${productId}">${skeletonHtml()}</div>
     </td>`;
  sourceRow.after(detailTr);

  setTimeout(() => detailTr.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 60);

  fetch('/api/products/' + productId)
    .then(r => r.json())
    .then(d => {
      const el = document.getElementById('detail-inner-' + productId);
      if (el) el.innerHTML = buildDetailHtml(d);
    })
    .catch(() => {
      const el = document.getElementById('detail-inner-' + productId);
      if (el) el.innerHTML = '<p style="color:#f87171;padding:12px 0;">Failed to load details.</p>';
    });
}

function skeletonHtml() {
  return [200,140,180,120,160,100].map(w =>
    `<div class="shimmer" style="width:${w}px;height:11px;border-radius:3px;margin-bottom:9px;display:inline-block;margin-right:16px;"></div>`
  ).join('');
}

function dField(label, value) {
  const missing = (value === null || value === undefined || value === '');
  return `<div class="df">
    <span class="df-lbl">${label}</span>
    ${missing ? '<span class="df-miss">not recorded</span>' : `<span class="df-val">${esc(String(value))}</span>`}
  </div>`;
}

function mkBadge(text, bg, color, border) {
  return `<span class="d-badge" style="background:${bg};color:${color};border-color:${border};">${esc(text)}</span>`;
}

function buildDetailHtml(d) {
  const stockBadge = d.in_stock
    ? mkBadge('In Stock',      '#052e16','#34d399','#16a34a')
    : mkBadge('Out of Stock',  '#3b0764','#a78bfa','#7c3aed');

  const citesBadge = d.cites_listed
    ? mkBadge('CITES Listed',     '#450a0a','#f87171','#dc2626')
    : mkBadge('Not CITES Listed', '#052e16','#34d399','#16a34a');

  const catBadge = mkBadge(d.category, d.cat_bg, d.cat_text, d.cat_border);

  const updHtml = d.stale_date
    ? `<span style="font-size:11px;color:${d.stale_color};">Updated ${esc(d.stale_date)}</span>`
    : `<span class="df-miss">No update date</span>`;

  // Aliases grouped by language
  const langLabels = {english:'English',swedish:'Swedish',portuguese:'Portuguese',vendor:'Vendor',other:'Other'};
  const aliasRows = Object.entries(d.aliases || {}).map(([lang, names]) =>
    dField(langLabels[lang] || lang, names.join(', '))
  ).join('') || dField('Known names', null);

  // Siblings table
  let siblingsHtml;
  if (!d.siblings || d.siblings.length === 0) {
    siblingsHtml = '<p class="df-miss" style="margin:6px 0 0;">No other listings for this species.</p>';
  } else {
    const sibRows = d.siblings.map(s => {
      const catSpan = `<span style="display:inline-flex;align-items:center;font-size:10px;font-weight:500;
        background:${s.cat_bg};color:${s.cat_text};border:1px solid ${s.cat_border};
        border-radius:20px;padding:1px 7px;white-space:nowrap;">${esc(s.category)}</span>`;
      const dot = s.in_stock
        ? '<span style="color:#34d399;" title="In stock">&#9679;</span>'
        : '<span style="color:#52525b;" title="Out of stock">&#9679;</span>';
      const lnk = s.url
        ? `<a href="${esc(s.url)}" target="_blank" class="view-link" onclick="event.stopPropagation()">&#8599;</a>`
        : '<span class="df-miss">-</span>';
      return `<tr class="sib-row" onclick="sibClick(${s.product_id})" title="Show details">
        <td style="white-space:nowrap;">${esc(s.vendor)} ${s.vendor_flag}</td>
        <td>${catSpan}</td>
        <td class="dim">${esc(s.format||'-')}</td>
        <td class="dim">${esc(s.grade||'-')}</td>
        <td class="dim">${esc(s.dimensions||'-')}</td>
        <td style="font-weight:600;white-space:nowrap;color:#f4f4f5;">
          ${s.price.toFixed(2)}<span style="color:#52525b;font-size:10px;margin-left:2px;">SEK</span></td>
        <td style="text-align:center;">${dot}</td>
        <td>${lnk}</td>
      </tr>`;
    }).join('');
    siblingsHtml = `<table class="sib-table">
      <thead><tr>
        <th>Vendor</th><th>Category</th><th>Format</th><th>Grade</th>
        <th>Dimensions</th><th>Price</th><th style="text-align:center;">Stock</th><th>Link</th>
      </tr></thead><tbody>${sibRows}</tbody></table>`;
  }

  const vendorWebHtml = d.vendor_website
    ? `<div class="df"><span class="df-lbl">Website</span>
        <a href="${esc(d.vendor_website)}" target="_blank" class="view-link">${esc(d.vendor_website)} &#8599;</a></div>`
    : dField('Website', null);

  const productUrlHtml = d.url
    ? `<div class="df"><span class="df-lbl">Product URL</span>
        <a href="${esc(d.url)}" target="_blank" class="view-link">View on vendor site &#8599;</a></div>`
    : dField('Product URL', null);

  return `
<div class="detail-wrap">
  <!-- Top bar: species name + price + badges + close -->
  <div class="detail-topbar">
    <div class="detail-topbar-left">
      <div class="detail-species-h">${esc(d.commercial_name || d.scientific_name)}</div>
      <div class="detail-sci-h">${esc(d.scientific_name)}</div>
      <div class="detail-badges-row">
        ${stockBadge} ${citesBadge} ${catBadge} ${updHtml}
      </div>
    </div>
    <div class="detail-topbar-right">
      <div class="detail-price-hero">
        <span class="detail-price-num">${d.price.toFixed(2)}</span>
        <span class="detail-price-cur">SEK</span>
        ${d.unit ? `<span class="detail-price-unit">/ ${esc(d.unit)}</span>` : ''}
      </div>
      <button class="detail-close-btn" onclick="closeDetail()">&#10005; Close</button>
    </div>
  </div>

  <!-- Three-column data grid -->
  <div class="detail-grid">
    <div class="detail-col">
      <div class="detail-col-hd">Product</div>
      ${dField('Format',     d.format)}
      ${dField('Grade',      d.grade)}
      ${dField('Unit',       d.unit)}
      ${dField('Dimensions', d.dimensions || null)}
      ${dField('Thickness',  d.thickness_mm != null ? d.thickness_mm + ' mm' : null)}
      ${dField('Width',      d.width_mm    != null ? d.width_mm    + ' mm' : null)}
      ${dField('Length',     d.length_mm   != null ? d.length_mm   + ' mm' : null)}
      ${dField('Weight',     d.weight_kg   != null ? d.weight_kg   + ' kg' : null)}
      ${dField('Listed as',  d.species_as_listed)}
      ${productUrlHtml}
    </div>

    <div class="detail-col">
      <div class="detail-col-hd">Vendor</div>
      ${dField('Name',     d.vendor + ' ' + d.vendor_flag)}
      ${dField('Country',  d.vendor_country)}
      ${dField('Currency', d.vendor_currency)}
      ${vendorWebHtml}
      <div class="detail-col-hd" style="margin-top:18px;">Species</div>
      ${dField('Scientific',      d.scientific_name)}
      ${dField('Commercial',      d.commercial_name)}
      ${dField('Alt. commercial', d.alt_commercial_name)}
      ${dField('Origin',          d.origin)}
      <div class="df"><span class="df-lbl">CITES</span>${citesBadge}</div>
    </div>

    <div class="detail-col">
      <div class="detail-col-hd">Known Names</div>
      ${aliasRows}
    </div>
  </div>

  <!-- Other listings: full width -->
  <div class="detail-siblings">
    <div class="detail-col-hd">
      Other listings for this species
      <span class="sib-count">${d.siblings.length} found</span>
    </div>
    ${siblingsHtml}
  </div>
</div>`;
}

/* Click a sibling row — navigate to that product's detail */
function sibClick(productId) {
  // Check if it's on the current page
  const targetRow = document.querySelector(`tr.data-row[data-pid="${productId}"]`);
  if (targetRow) {
    toggleDetail(productId, targetRow);
    return;
  }
  // Not on current page: just reload the expansion content in place
  const inner = document.querySelector('.detail-expand-inner');
  if (inner) {
    inner.innerHTML = skeletonHtml();
    expandedProductId = productId;
    fetch('/api/products/' + productId)
      .then(r => r.json())
      .then(d => { inner.innerHTML = buildDetailHtml(d); inner.scrollIntoView({behavior:'smooth',block:'nearest'}); })
      .catch(() => { inner.innerHTML = '<p style="color:#f87171;">Failed to load.</p>'; });
  }
}

/* Escape key */
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeDetail(); });

/* ===================== RENDER ROWS ===================== */

function renderRows(rows) {
  const tbody = document.getElementById('tbody');
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="no-results">No products match your filters.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(p => `<tr class="data-row" data-pid="${p.product_id}"
      onclick="toggleDetail(${p.product_id}, this)" title="Click to expand details">
    <td>
      <div class="species-name">${esc(p.species)}</div>
      ${p.alias ? `<div class="species-alias">listed as: ${esc(p.alias)}</div>` : ''}
    </td>
    <td class="vendor-name">${esc(p.vendor)} ${p.vendor_flag}</td>
    <td><span style="display:inline-flex;align-items:center;font-size:11px;font-weight:500;
      background:${p.cat_bg};color:${p.cat_text};border:1px solid ${p.cat_border};
      border-radius:20px;padding:2px 8px;white-space:nowrap;">${esc(p.category)}</span></td>
    <td class="dim">${esc(p.format || '-')}</td>
    <td class="dim">${esc(p.grade  || '-')}</td>
    <td><span class="price-val">${p.price.toFixed(2)}</span><span class="price-cur">SEK</span></td>
    <td style="font-size:11px;color:${p.stale_color};white-space:nowrap;">${p.stale_date || '-'}</td>
    <td>${p.url
      ? `<a href="${esc(p.url)}" target="_blank" class="view-link" onclick="event.stopPropagation()">View &#8599;</a>`
      : '<span class="dim">-</span>'}</td>
  </tr>`).join('');
}

/* ===================== PAGER ===================== */

function renderPager(page, pages) {
  const pagers = [document.getElementById('pager-top'), document.getElementById('pager')];
  if (pages <= 1) { pagers.forEach(p => { if (p) p.innerHTML = ''; }); return; }
  const toShow = new Set([1, pages]);
  for (let p = Math.max(2,page-2); p <= Math.min(pages-1,page+2); p++) toShow.add(p);
  const sorted = [...toShow].sort((a,b)=>a-b);
  let html = `<button class="page-btn" onclick="goToPage(${page-1})" ${page===1?'disabled':''}>&larr; Prev</button>`;
  let prev = 0;
  for (const p of sorted) {
    if (p > prev+1) html += '<span class="page-ellipsis">&hellip;</span>';
    html += `<button class="page-num${p===page?' active':''}" onclick="goToPage(${p})">${p}</button>`;
    prev = p;
  }
  html += `<button class="page-btn" onclick="goToPage(${page+1})" ${page===pages?'disabled':''}>Next &rarr;</button>`;
  pagers.forEach(p => { if (p) p.innerHTML = html; });
}

function updateFormatDropdown(formats) {
  const group = document.getElementById('format-group');
  const select = document.getElementById('f-format');
  if (!formats || !formats.length) { group.style.display = 'none'; return; }
  group.style.display = 'flex';
  select.innerHTML = '<option value="">All formats</option>' +
    formats.map(f => `<option value="${f.id}"${f.id===state.format_id?' selected':''}>${esc(f.name)} (${f.count})</option>`).join('');
}

function showLoading() {
  document.getElementById('tbody').innerHTML = Array(8).fill(`<tr class="loading-row">
    ${Array(8).fill('<td><div class="shimmer"></div></td>').join('')}
  </tr>`).join('');
}

function toggleFilters() {
  const panel = document.getElementById('filter-panel');
  const label = document.getElementById('toggle-label');
  const arrow = document.getElementById('toggle-arrow');
  const hidden = panel.style.display === 'none';
  panel.style.display = hidden ? 'block' : 'none';
  label.textContent = hidden ? 'Hide filters' : 'Show filters';
  arrow.textContent = hidden ? 'up' : 'down';
}

function fetchAndRender() {
  renderChips();
  updateSortHeaders();
  showLoading();
  const params = new URLSearchParams();
  if (state.species_id)  params.set('species_id',  state.species_id);
  if (state.vendor_id)   params.set('vendor_id',   state.vendor_id);
  if (state.category_id) params.set('category_id', state.category_id);
  if (state.format_id)   params.set('format_id',   state.format_id);
  if (state.max_price)   params.set('max_price',   state.max_price);
  params.set('sort', state.sort);
  params.set('order', state.order);
  params.set('page', state.page);
  fetch('/api/products?' + params)
    .then(r => r.json())
    .then(data => {
      renderRows(data.rows);
      renderPager(data.page, data.pages);
      const start = (data.page-1)*50+1, end = Math.min(data.page*50, data.total);
      document.getElementById('results-text').innerHTML =
        `Showing <strong>${start}&ndash;${end}</strong> of <strong>${data.total}</strong> products`;
      document.getElementById('footer-count').textContent = data.total + ' products';
      if (state.category_id) updateFormatDropdown(data.formats);
    })
    .catch(() => {
      document.getElementById('tbody').innerHTML =
        '<tr><td colspan="8" class="no-results">Error loading products.</td></tr>';
    });
}

fetchAndRender();