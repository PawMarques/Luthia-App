const state = {
  species_id: null, vendor_id: null, category_id: null,
  format_id: null, max_price: null,
  sort: 'price', order: 'asc', page: 1,
};
const labels = {};

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
    if (state.max_price) labels.price = '≤ ' + Math.round(state.max_price) + ' SEK';
    else delete labels.price;
    fetchAndRender();
  }, 400);
}

function sortBy(col) {
  state.order = (state.sort === col && state.order === 'asc') ? 'desc' : 'asc';
  state.sort = col;
  state.page = 1;
  fetchAndRender();
}

function goToPage(p) {
  state.page = p;
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
  fetchAndRender();
}

function renderChips() {
  const row = document.getElementById('chips-row');
  const active = Object.entries(labels);
  if (!active.length) { row.innerHTML = ''; return; }
  let html = active.map(([k,l]) =>
    `<span class="chip">${esc(l)}<span class="chip-x" onclick="clearFilter('${k}')">×</span></span>`
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
      th.textContent = base + (state.order === 'asc' ? ' ↑' : ' ↓');
    } else {
      th.classList.remove('sorted');
      th.textContent = base;
    }
  });
}

function renderRows(rows) {
  const tbody = document.getElementById('tbody');
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="no-results">No products match your filters.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(p => `<tr>
    <td>
      <div class="species-name">${esc(p.species)}</div>
      ${p.alias ? `<div class="species-alias">listed as: ${esc(p.alias)}</div>` : ''}
    </td>
    <td class="vendor-name">${esc(p.vendor)} ${p.vendor_flag}</td>
    <td><span style="display:inline-flex;align-items:center;font-size:11px;font-weight:500;
      background:${p.cat_bg};color:${p.cat_text};border:1px solid ${p.cat_border};
      border-radius:20px;padding:2px 8px;white-space:nowrap;">${esc(p.category)}</span></td>
    <td class="dim">${esc(p.format || '—')}</td>
    <td class="dim">${esc(p.grade  || '—')}</td>
    <td><span class="price-val">${p.price.toFixed(2)}</span><span class="price-cur">SEK</span></td>
    <td style="font-size:11px;color:${p.stale_color};white-space:nowrap;">${p.stale_date || '—'}</td>
    <td>${p.url ? `<a href="${esc(p.url)}" target="_blank" class="view-link">View ↗</a>` : '<span class="dim">—</span>'}</td>
  </tr>`).join('');
}

function renderPager(page, pages) {
  const pager = document.getElementById('pager');
  if (pages <= 1) { pager.innerHTML = ''; return; }
  const toShow = new Set([1, pages]);
  for (let p = Math.max(2,page-2); p <= Math.min(pages-1,page+2); p++) toShow.add(p);
  const sorted = [...toShow].sort((a,b)=>a-b);
  let html = `<button class="page-btn" onclick="goToPage(${page-1})" ${page===1?'disabled':''}>← Prev</button>`;
  let prev = 0;
  for (const p of sorted) {
    if (p > prev+1) html += '<span class="page-ellipsis">…</span>';
    html += `<button class="page-num${p===page?' active':''}" onclick="goToPage(${p})">${p}</button>`;
    prev = p;
  }
  html += `<button class="page-btn" onclick="goToPage(${page+1})" ${page===pages?'disabled':''}>Next →</button>`;
  pager.innerHTML = html;
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
  arrow.textContent = hidden ? '↑' : '↓';
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
        `Showing <strong>${start}–${end}</strong> of <strong>${data.total}</strong> products`;
      document.getElementById('footer-count').textContent = data.total + ' products';
      if (state.category_id) updateFormatDropdown(data.formats);
    })
    .catch(() => {
      document.getElementById('tbody').innerHTML =
        '<tr><td colspan="8" class="no-results">Error loading products.</td></tr>';
    });
}

fetchAndRender();
