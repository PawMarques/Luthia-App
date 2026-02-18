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

  const vendorWebHtml = d.vendor_website
    ? `<div class="df"><span class="df-lbl">Website</span>
        <a href="${esc(d.vendor_website)}" target="_blank" class="view-link">${esc(d.vendor_website)} &#8599;</a></div>`
    : dField('Website', null);

  const productUrlHtml = d.url
    ? `<div class="df"><span class="df-lbl">Product URL</span>
        <a href="${esc(d.url)}" target="_blank" class="view-link">View on vendor site &#8599;</a></div>`
    : dField('Product URL', null);

  return `
<div class="detail-wrap" data-product-id="${d.product_id}">
  <!-- Top bar -->
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
      <button class="edit-btn" onclick="enterEditMode(${d.product_id})">&#9998; Edit</button>
    </div>
  </div>

  <!-- Images section -->
  <div class="img-section" id="img-section-${d.product_id}">
    ${buildImagesHtml(d.images, d.product_id, false)}
  </div>

  <!-- View mode grid -->
  <div class="detail-grid" id="view-grid-${d.product_id}">
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

  <!-- Edit mode grid (hidden until Edit clicked) -->
  <div class="detail-grid edit-grid" id="edit-grid-${d.product_id}" style="display:none;">
    <div class="detail-col">
      <div class="detail-col-hd">Product <span style="color:#3b82f6;font-style:italic;font-weight:400;text-transform:none;letter-spacing:0;">— editable</span></div>
      ${eField('Price (SEK)', 'edit-price',     d.price,        'number')}
      ${eField('Format',      'edit-format',    d.format,       'text')}
      ${eField('Grade',       'edit-grade',     d.grade,        'text')}
      ${eField('Thickness mm','edit-thickness', d.thickness_mm, 'number')}
      ${eField('Width mm',    'edit-width',     d.width_mm,     'number')}
      ${eField('Length mm',   'edit-length',    d.length_mm,    'number')}
      ${eField('Weight kg',   'edit-weight',    d.weight_kg,    'number')}
      ${eField('Product URL', 'edit-url',       d.url,          'text', true)}
      <div class="df" style="margin-top:6px;">
        <span class="df-lbl">In Stock</span>
        <label class="edit-toggle">
          <input type="checkbox" id="edit-instock" ${d.in_stock ? 'checked' : ''}>
          <span class="edit-toggle-track">
            <span class="edit-toggle-thumb"></span>
          </span>
          <span class="edit-toggle-label" id="edit-instock-label">${d.in_stock ? 'Yes' : 'No'}</span>
        </label>
      </div>
    </div>
    <div class="detail-col">
      <div class="detail-col-hd">Vendor</div>
      ${dField('Name',     d.vendor + ' ' + d.vendor_flag)}
      ${dField('Country',  d.vendor_country)}
      <p class="edit-note">Vendor details are managed via the import script.</p>
      <div class="detail-col-hd" style="margin-top:18px;">Species</div>
      ${dField('Scientific',  d.scientific_name)}
      ${dField('Commercial',  d.commercial_name)}
      ${dField('Origin',      d.origin)}
      <p class="edit-note">Species data is managed via the species sheet.</p>
    </div>
    <div class="detail-col">
      <div class="detail-col-hd">Known Names</div>
      ${aliasRows}
      <p class="edit-note">Names are managed via the species sheet.</p>
    </div>
  </div>

  <!-- Save / Cancel bar (hidden until Edit clicked) -->
  <div class="edit-action-bar" id="edit-bar-${d.product_id}" style="display:none;">
    <span class="edit-error" id="edit-error-${d.product_id}"></span>
    <div class="edit-action-btns">
      <button class="edit-cancel-btn" onclick="cancelEditMode(${d.product_id})">Cancel</button>
      <button class="edit-save-btn"   onclick="saveEdit(${d.product_id})">&#10003; Save changes</button>
    </div>
  </div>
</div>`;
}

/* Input field for edit mode */
function eField(label, id, value, type, wide) {
  const v = (value !== null && value !== undefined && value !== '') ? value : '';
  return `<div class="df ${wide ? 'df-wide' : ''}">
    <span class="df-lbl">${label}</span>
    <input class="edit-input ${type === 'number' ? 'edit-input-num' : 'edit-input-text'}"
           id="${id}" type="${type}" value="${esc(String(v))}"
           step="${type === 'number' ? 'any' : undefined}"
           placeholder="${v === '' ? 'not recorded' : ''}">
  </div>`;
}

/* ===================== IMAGES ===================== */

function buildImagesHtml(images, productId, editMode) {
  const thumbs = (images || []).map(img => `
    <div class="img-thumb-wrap" id="img-wrap-${img.image_id}">
      <img class="img-thumb" src="${esc(img.src)}"
           alt="${esc(img.caption || 'Product image')}"
           onclick="openLightbox('${esc(img.src)}')"
           onerror="this.closest('.img-thumb-wrap').classList.add('img-error')">
      ${img.caption ? `<div class="img-caption">${esc(img.caption)}</div>` : ''}
      ${editMode ? `
        <button class="img-delete-btn" onclick="deleteImage(${img.image_id}, ${productId})"
                title="Remove image">&#10005;</button>` : ''}
    </div>`).join('');

  const uploadArea = editMode ? `
    <div class="img-upload-area" id="img-upload-area-${productId}"
         onclick="document.getElementById('img-file-input-${productId}').click()"
         ondragover="event.preventDefault();this.classList.add('drag-over')"
         ondragleave="this.classList.remove('drag-over')"
         ondrop="handleImageDrop(event,${productId})">
      <input type="file" id="img-file-input-${productId}" accept="image/*" style="display:none"
             onchange="handleImageFile(this,${productId})">
      <span class="img-upload-icon">&#128247;</span>
      <span class="img-upload-hint">Click or drop image</span>
    </div>
    <div class="img-url-row">
      <input class="edit-input edit-input-text" id="img-url-input-${productId}"
             placeholder="…or paste an image URL" type="url"
             onkeydown="if(event.key==='Enter')addImageUrl(${productId})">
      <button class="img-url-btn" onclick="addImageUrl(${productId})">Add URL</button>
    </div>
    <div class="img-upload-error" id="img-upload-error-${productId}"></div>` : '';

  const empty = (!images || images.length === 0) && !editMode
    ? `<span class="df-miss" style="font-size:12px;">No images</span>` : '';

  return `
    <div class="img-section-inner">
      <div class="img-thumbs-row" id="img-thumbs-${productId}">${thumbs}${empty}</div>
      ${uploadArea}
    </div>`;
}

function refreshImageSection(productId, editMode) {
  fetch('/api/products/' + productId)
    .then(r => r.json())
    .then(d => {
      const el = document.getElementById('img-section-' + productId);
      if (el) el.innerHTML = buildImagesHtml(d.images, productId, editMode);
    });
}

function handleImageFile(input, productId) {
  const file = input.files[0];
  if (!file) return;
  const form = new FormData();
  form.append('file', file);
  uploadImage(productId, form);
  input.value = '';
}

function handleImageDrop(event, productId) {
  event.preventDefault();
  document.getElementById('img-upload-area-' + productId).classList.remove('drag-over');
  const file = event.dataTransfer.files[0];
  if (!file) return;
  const form = new FormData();
  form.append('file', file);
  uploadImage(productId, form);
}

function addImageUrl(productId) {
  const input = document.getElementById('img-url-input-' + productId);
  const url = (input.value || '').trim();
  if (!url) return;
  setImgError(productId, '');
  fetch('/api/products/' + productId + '/images', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ url }),
  })
  .then(r => r.json())
  .then(data => {
    if (!data.ok) { setImgError(productId, data.error || 'Failed to add URL.'); return; }
    input.value = '';
    refreshImageSection(productId, true);
  })
  .catch(() => setImgError(productId, 'Network error.'));
}

function uploadImage(productId, formData) {
  setImgError(productId, '');
  const area = document.getElementById('img-upload-area-' + productId);
  if (area) area.classList.add('uploading');
  fetch('/api/products/' + productId + '/images', { method: 'POST', body: formData })
    .then(r => r.json())
    .then(data => {
      if (area) area.classList.remove('uploading');
      if (!data.ok) { setImgError(productId, data.error || 'Upload failed.'); return; }
      refreshImageSection(productId, true);
    })
    .catch(() => {
      if (area) area.classList.remove('uploading');
      setImgError(productId, 'Network error during upload.');
    });
}

function deleteImage(imageId, productId) {
  if (!confirm('Remove this image?')) return;
  fetch('/api/images/' + imageId, { method: 'DELETE' })
    .then(r => r.json())
    .then(data => {
      if (!data.ok) return;
      refreshImageSection(productId, true);
    });
}

function setImgError(productId, msg) {
  const el = document.getElementById('img-upload-error-' + productId);
  if (el) el.textContent = msg;
}

/* Lightbox */
function openLightbox(src) {
  let lb = document.getElementById('lightbox');
  if (!lb) {
    lb = document.createElement('div');
    lb.id = 'lightbox';
    lb.className = 'lightbox';
    lb.innerHTML = '<div class="lightbox-bg"></div><img class="lightbox-img"><button class="lightbox-close">&#10005;</button>';
    lb.querySelector('.lightbox-bg').onclick  = closeLightbox;
    lb.querySelector('.lightbox-close').onclick = closeLightbox;
    document.body.appendChild(lb);
  }
  lb.querySelector('.lightbox-img').src = src;
  lb.classList.add('open');
  document.body.style.overflow = 'hidden';
}
function closeLightbox() {
  const lb = document.getElementById('lightbox');
  if (lb) lb.classList.remove('open');
  document.body.style.overflow = '';
}
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') { closeLightbox(); closeDetail(); }
});

/* ---- Edit mode transitions ---- */

function enterEditMode(productId) {
  document.getElementById('view-grid-' + productId).style.display = 'none';
  document.getElementById('edit-grid-' + productId).style.display = '';
  document.getElementById('edit-bar-'  + productId).style.display = '';

  // Switch image section to edit mode
  refreshImageSection(productId, true);

  // Wire up the stock toggle label
  const cb = document.getElementById('edit-instock');
  const lbl = document.getElementById('edit-instock-label');
  cb.addEventListener('change', () => { lbl.textContent = cb.checked ? 'Yes' : 'No'; });

  // Swap edit button to disabled state
  const btn = document.querySelector(`.detail-wrap[data-product-id="${productId}"] .edit-btn`);
  if (btn) { btn.disabled = true; btn.style.opacity = '0.35'; }

  // Focus price field
  setTimeout(() => { const el = document.getElementById('edit-price'); if (el) el.focus(); }, 50);
}

function cancelEditMode(productId) {
  document.getElementById('view-grid-' + productId).style.display = '';
  document.getElementById('edit-grid-' + productId).style.display = 'none';
  document.getElementById('edit-bar-'  + productId).style.display = 'none';
  document.getElementById('edit-error-'+ productId).textContent = '';

  // Switch image section back to view mode
  refreshImageSection(productId, false);

  const btn = document.querySelector(`.detail-wrap[data-product-id="${productId}"] .edit-btn`);
  if (btn) { btn.disabled = false; btn.style.opacity = ''; }
}

function saveEdit(productId) {
  const saveBtn = document.querySelector(`#edit-bar-${productId} .edit-save-btn`);
  const errEl   = document.getElementById('edit-error-' + productId);
  errEl.textContent = '';
  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving…';

  const payload = {
    price:        document.getElementById('edit-price').value,
    in_stock:     document.getElementById('edit-instock').checked,
    format:       document.getElementById('edit-format').value,
    grade:        document.getElementById('edit-grade').value,
    thickness_mm: document.getElementById('edit-thickness').value,
    width_mm:     document.getElementById('edit-width').value,
    length_mm:    document.getElementById('edit-length').value,
    weight_kg:    document.getElementById('edit-weight').value,
    product_url:  document.getElementById('edit-url').value,
  };

  fetch('/api/products/' + productId, {
    method:  'PUT',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(payload),
  })
  .then(r => r.json())
  .then(data => {
    if (!data.ok) {
      errEl.textContent = data.errors ? data.errors.join(' ') : 'Save failed.';
      saveBtn.disabled = false;
      saveBtn.textContent = '\u2713 Save changes';
      return;
    }
    // Reload the detail panel with fresh data and exit edit mode
    const inner = document.getElementById('detail-inner-' + productId);
    if (inner) inner.innerHTML = skeletonHtml();
    fetch('/api/products/' + productId)
      .then(r => r.json())
      .then(d => {
        if (inner) inner.innerHTML = buildDetailHtml(d);
        // Also refresh the table row in the background so price/stock reflect immediately
        fetchAndRender();
      });
  })
  .catch(() => {
    errEl.textContent = 'Network error — changes not saved.';
    saveBtn.disabled = false;
    saveBtn.textContent = '\u2713 Save changes';
  });
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