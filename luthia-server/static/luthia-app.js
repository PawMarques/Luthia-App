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
  const content = document.querySelector('.page-content');
  if (content) content.scrollTop = 0;
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

  fetch('/api/v1/products/' + productId)
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

  const catBadge = `<span class="cat-badge ${esc(d.cat_class)}">${esc(d.category)}</span>`;

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

  // 7: Vendor line for top bar (flag + name + country)
  const vendorLine = `<div class="detail-vendor-line">
    <span class="detail-vendor-name">${esc(d.vendor)}</span>
    <span class="detail-vendor-flag">${d.vendor_flag}</span>
    <span class="detail-vendor-country">${esc(d.vendor_country)}</span>
  </div>`;

  return `
<div class="detail-wrap" data-product-id="${d.product_id}">

  <!-- Top bar: 2-column, species left, price+vendor right, aligned to baseline -->
  <div class="detail-topbar">
    <div class="detail-topbar-left">
      <div class="detail-species-h">${esc(d.commercial_name || d.scientific_name)}</div>
      <div class="detail-sci-h">${esc(d.scientific_name)}</div>
      <div class="detail-badges-row">
        ${stockBadge} ${catBadge} ${updHtml}
      </div>
    </div>
    <div class="detail-topbar-right">
      <div class="detail-price-hero">
        <span class="detail-price-num">${d.price.toFixed(2)}</span>
        <span class="detail-price-cur">SEK</span>
        ${d.unit ? `<span class="detail-price-unit">/ ${esc(d.unit)}</span>` : ''}
      </div>
      ${vendorLine}
    </div>
  </div>

  <!-- View mode grid: Product | Images | gap | Species+Names -->
  <div class="detail-grid" id="view-grid-${d.product_id}">
    <div class="detail-col detail-col-editable">
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
    <div class="detail-col detail-col-images detail-col-editable" id="img-section-${d.product_id}">
      <div class="detail-col-hd">Images</div>
      ${buildImagesHtml(d.images, d.product_id, false)}
    </div>
    <div class="detail-col detail-col-gap"></div>
    <div class="detail-col detail-col-readonly">
      <div class="detail-col-hd">Species</div>
      ${dField('Scientific', d.scientific_name)}
      ${dField('Commercial', d.commercial_name)}
      ${dField('Origin',     d.origin)}
      <div class="df"><span class="df-lbl">CITES</span>${citesBadge}</div>
      <div class="detail-col-hd" style="margin-top:18px;">Known Names</div>
      ${d.alt_commercial_name ? dField('Alt. commercial', d.alt_commercial_name) : ''}
      ${aliasRows}
    </div>
  </div>

  <!-- Edit mode grid -->
  <div class="detail-grid edit-grid" id="edit-grid-${d.product_id}" style="display:none;">
    <div class="detail-col detail-col-editable">
      <div class="detail-col-hd">Product <span class="edit-col-tag">editable</span></div>
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
          <span class="edit-toggle-track"><span class="edit-toggle-thumb"></span></span>
          <span class="edit-toggle-label" id="edit-instock-label">${d.in_stock ? 'Yes' : 'No'}</span>
        </label>
      </div>
    </div>
    <div class="detail-col detail-col-images detail-col-editable">
      <div class="detail-col-hd">Images <span class="edit-col-tag">editable</span></div>
    </div>
    <div class="detail-col detail-col-gap"></div>
    <div class="detail-col detail-col-readonly">
      <div class="detail-col-hd">Species</div>
      ${dField('Scientific', d.scientific_name)}
      ${dField('Commercial', d.commercial_name)}
      ${dField('Origin',     d.origin)}
      <div class="df"><span class="df-lbl">CITES</span>${citesBadge}</div>
      <div class="detail-col-hd" style="margin-top:18px;">Known Names</div>
      ${d.alt_commercial_name ? dField('Alt. commercial', d.alt_commercial_name) : ''}
      ${aliasRows}
    </div>
  </div>

  <!-- Action bar: Edit + Cancel + Save all left-aligned -->
  <div class="edit-action-bar" id="edit-bar-${d.product_id}">
    <button class="edit-btn" id="edit-btn-${d.product_id}" onclick="enterEditMode(${d.product_id})">&#9998; Edit</button>
    <div class="edit-action-btns" id="edit-save-btns-${d.product_id}" style="display:none;">
      <button class="edit-cancel-btn" onclick="cancelEditMode(${d.product_id})">Cancel</button>
      <button class="edit-save-btn"   onclick="saveEdit(${d.product_id})">&#10003; Save changes</button>
    </div>
    <span class="edit-error" id="edit-error-${d.product_id}"></span>
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
      <span class="img-upload-hint">Click or drop</span>
    </div>` : '';

  const empty = (!images || images.length === 0) && !editMode
    ? `<span class="df-miss" style="font-size:12px;">No images</span>` : '';

  return `
    <div class="img-section-inner">
      <div class="img-thumbs-row" id="img-thumbs-${productId}">${thumbs}${uploadArea}${empty}</div>
      <div class="img-upload-error" id="img-upload-error-${productId}"></div>
    </div>`;
}

function refreshImageSection(productId, editMode) {
  fetch('/api/v1/products/' + productId)
    .then(r => r.json())
    .then(d => {
      const gridId  = editMode ? 'edit-grid-' : 'view-grid-';
      const col = document.querySelector(`#${gridId}${productId} .detail-col-images`);
      if (!col) return;
      const hd = col.querySelector('.detail-col-hd');
      while (col.children.length > 1) col.removeChild(col.lastChild);
      const inner = document.createElement('div');
      inner.innerHTML = buildImagesHtml(d.images, productId, editMode);
      col.appendChild(inner);
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
  fetch('/api/v1/products/' + productId + '/images', {
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
  fetch('/api/v1/products/' + productId + '/images', { method: 'POST', body: formData })
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
  fetch('/api/v1/images/' + imageId, { method: 'DELETE' })
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

  // Show Save/Cancel, disable Edit button
  document.getElementById('edit-save-btns-' + productId).style.display = '';
  const editBtn = document.getElementById('edit-btn-' + productId);
  if (editBtn) { editBtn.disabled = true; editBtn.style.opacity = '0.35'; }

  // Populate the images column in the edit grid
  const editImgCol = document.querySelector(`#edit-grid-${productId} .detail-col-images`);
  if (editImgCol) {
    fetch('/api/v1/products/' + productId)
      .then(r => r.json())
      .then(d => {
        const inner = document.createElement('div');
        inner.innerHTML = buildImagesHtml(d.images, productId, true);
        while (editImgCol.children.length > 1) editImgCol.removeChild(editImgCol.lastChild);
        editImgCol.appendChild(inner);
      });
  }

  // Wire up the stock toggle label
  const cb = document.getElementById('edit-instock');
  const lbl = document.getElementById('edit-instock-label');
  if (cb) cb.addEventListener('change', () => { lbl.textContent = cb.checked ? 'Yes' : 'No'; });

  setTimeout(() => { const el = document.getElementById('edit-price'); if (el) el.focus(); }, 50);
}

function cancelEditMode(productId) {
  document.getElementById('view-grid-' + productId).style.display = '';
  document.getElementById('edit-grid-' + productId).style.display = 'none';
  document.getElementById('edit-error-'+ productId).textContent = '';

  // Hide Save/Cancel, re-enable Edit button
  document.getElementById('edit-save-btns-' + productId).style.display = 'none';
  const editBtn = document.getElementById('edit-btn-' + productId);
  if (editBtn) { editBtn.disabled = false; editBtn.style.opacity = ''; }
}

function saveEdit(productId) {
  const saveBtn = document.querySelector(`#edit-save-btns-${productId} .edit-save-btn`);
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

  fetch('/api/v1/products/' + productId, {
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
    fetch('/api/v1/products/' + productId)
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
    <td><span class="cat-badge ${esc(p.cat_class)}">${esc(p.category)}</span></td>
    <td class="dim">${esc(p.format || '-')}</td>
    <td class="dim">${esc(p.grade  || '-')}</td>
    <td><span class="price-val">${p.price.toFixed(2)}</span><span class="price-cur">SEK</span></td>
    <td style="font-size:11px;color:${p.stale_color};white-space:nowrap;">${p.stale_date || '-'}</td>
    <td>${p.url
      ? `<a href="${esc(p.url)}" target="_blank" class="view-link" onclick="event.stopPropagation()">View &#8599;</a>`
      : '<span class="dim">-</span>'}</td>
  </tr>`).join('');
}

/* ===================== SHARED PAGINATION ===================== */

function renderPagination(containerId, page, pages, navFnName) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (pages <= 1) { el.innerHTML = ''; return; }

  const pageSet = new Set([1, pages]);
  for (let p = Math.max(2, page-2); p <= Math.min(pages-1, page+2); p++) pageSet.add(p);
  const pageList = [...pageSet].sort((a, b) => a - b);

  let html = `<button class="page-btn" onclick="${navFnName}(${page-1})" ${page===1?'disabled':''}>&larr; Prev</button>`;
  let prev = 0;
  for (const p of pageList) {
    if (p > prev + 1) html += '<span class="page-ellipsis">&hellip;</span>';
    html += `<button class="page-num${p===page?' active':''}" onclick="${navFnName}(${p})">${p}</button>`;
    prev = p;
  }
  html += `<button class="page-btn" onclick="${navFnName}(${page+1})" ${page===pages?'disabled':''}>Next &rarr;</button>`;
  el.innerHTML = html;
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
  fetch('/api/v1/products?' + params)
    .then(r => r.json())
    .then(data => {
      renderRows(data.rows);
      renderPagination('pager-bottom', data.page, data.pages, 'goToPage');
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

if (document.getElementById('tbody')) fetchAndRender();

/* ===================== SPECIES PAGE CONTROLLER ===================== */

const sgState = {
  q: '', filter: 'all', page: 1, loading: false, activeId: null,
};
let sgSearchTimer = null;

function goPage(p) {
  sgState.page = p;
  loadGrid();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function loadGrid() {
  if (sgState.loading) return;
  sgState.loading = true;

  const grid = document.getElementById('sg-grid');
  grid.innerHTML = '<div class="sg-loading">Loading…</div>';
  document.getElementById('sg-pagination').innerHTML = '';
  document.getElementById('sg-count').textContent = '';

  const params = new URLSearchParams({ page: sgState.page });
  if (sgState.q) params.set('q', sgState.q);
  if (sgState.filter === 'cites') params.set('cites', '1');
  if (sgState.filter === 'available') params.set('available', '1');

  const data = await fetch(`/api/v1/species?${params}`).then(r => r.json());
  sgState.loading = false;

  document.getElementById('sg-count').textContent =
    `${data.total} result${data.total !== 1 ? 's' : ''}`;

  if (data.rows.length === 0) {
    grid.innerHTML = `
      <div class="sg-empty">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.3">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        No species matched your search.
      </div>`;
    return;
  }

  grid.innerHTML = data.rows.map(renderCard).join('');

  if (sgState.activeId) {
    const el = document.getElementById(`sg-card-${sgState.activeId}`);
    if (el) el.classList.add('is-active');
  }

  renderPagination('sg-pagination', data.page, data.pages, 'goPage');
}

function renderCard(s) {
  const hasName = !!s.commercial_name;
  const title = hasName ? esc(s.commercial_name) : `<em>${esc(s.scientific_name)}</em>`;
  const subtitle = hasName ? esc(s.scientific_name) : '';

  const countHtml = s.total_products > 0
    ? `<span class="tpl-builds-count">${s.total_products} product${s.total_products !== 1 ? 's' : ''}</span>`
    : '';

  const actionsHtml = `
    <div style="display:flex;align-items:center;gap:10px;">
      ${countHtml}
      <button class="btn-sm" onclick="event.stopPropagation();openDrawer(${s.species_id})">Details</button>
      <a class="btn-sm btn-sm--accent" href="/browse?species_id=${s.species_id}">Browse</a>
    </div>`;

  const priceLabel = s.min_price != null
    ? (s.min_price === s.max_price
        ? fmtPrice(s.min_price)
        : fmtPrice(s.min_price) + ' – ' + fmtPrice(s.max_price))
    : 'Not available';

  const citesBadge = s.cites_listed
    ? `<span class="tpl-construction-badge">CITES</span>`
    : '';

  const originRow = s.origin
    ? `<div class="tpl-dim-row"><span>Origin</span><span>${esc(s.origin)}</span></div>`
    : '';

  let vendorRow;
  if (s.total_products > 0) {
    const pills = s.vendors.map(v =>
      `<span class="sg-vendor-pill">${v.flag} ${esc(v.name)}</span>`
    ).join('');
    vendorRow = `<div class="tpl-dim-row">
      <span>Vendors</span>
      <span style="display:flex;align-items:center;gap:5px;flex-wrap:wrap;">${pills}</span>
    </div>`;
  } else {
    vendorRow = `<div class="tpl-dim-row">
      <span>Vendors</span>
      <span class="sg-no-products">Not available from vendors</span>
    </div>`;
  }

  return `
<div class="tpl-card sg-card" id="sg-card-${s.species_id}">
  <div class="tpl-card-header">
    <div>
      <div class="tpl-card-title">${title}</div>
      ${subtitle ? `<div class="tpl-card-type">${subtitle}</div>` : ''}
    </div>
    ${actionsHtml}
  </div>
  <div class="tpl-variant">
    <div class="tpl-variant-header">
      <div>
        <span class="tpl-variant-label sg-price-label">${priceLabel}</span>
        ${citesBadge}
      </div>
    </div>
    <div class="tpl-dims">
      ${originRow}
      ${vendorRow}
    </div>
  </div>
</div>`;
}

function fmtPrice(p) {
  return p != null ? p.toFixed(0) + ' SEK' : '';
}

async function openDrawer(speciesId) {
  if (sgState.activeId) {
    const prev = document.getElementById(`sg-card-${sgState.activeId}`);
    if (prev) prev.classList.remove('is-active');
  }
  sgState.activeId = speciesId;

  const card = document.getElementById(`sg-card-${speciesId}`);
  if (card) card.classList.add('is-active');

  const backdrop = document.getElementById('sg-drawer-backdrop');
  backdrop.classList.add('is-open');
  document.getElementById('drawer-commercial').textContent = '…';
  document.getElementById('drawer-scientific').textContent = '';
  document.getElementById('drawer-badges').innerHTML = '';
  document.getElementById('sg-drawer-body').innerHTML = '<div class="sg-drawer-loading">Loading…</div>';

  const data = await fetch(`/api/v1/species/${speciesId}`).then(r => r.json());
  renderDrawer(data);
}

function renderDrawer(d) {
  document.getElementById('drawer-commercial').textContent =
    d.commercial_name || d.scientific_name;
  document.getElementById('drawer-scientific').textContent = d.scientific_name;

  const badges = [];
  if (d.cites_listed) badges.push(`<span class="badge-cites">CITES Listed</span>`);
  if (d.total_products > 0) {
    const inStk = d.in_stock_count > 0
      ? `<span class="badge-in-stock">${d.in_stock_count} in stock</span>`
      : `<span class="badge-out-stock">out of stock</span>`;
    badges.push(inStk);
  }
  document.getElementById('drawer-badges').innerHTML = badges.join('');

  let html = '';

  html += `<div>
    <div class="sg-section-title">Names</div>
    <div class="sg-names-grid">`;

  const nameRows = [
    ['Commercial', d.commercial_name, d.alt_commercial_name],
    ['English', d.english_name, d.alt_english_name],
    ['Swedish', d.swedish_name, d.alt_swedish_name],
    ['Portuguese', d.portuguese_name, d.alt_portuguese_name],
  ];
  for (const [lbl, primary, alt] of nameRows) {
    const val = [primary, alt].filter(Boolean).join(' · ') || null;
    html += `<div class="sg-name-row">
      <span class="sg-name-lbl">${lbl}</span>
      <span class="sg-name-val">${val ? esc(val) : '<em>—</em>'}</span>
    </div>`;
  }
  if (d.origin) {
    html += `<div class="sg-name-row">
      <span class="sg-name-lbl">Origin</span>
      <span class="sg-name-val">${esc(d.origin)}</span>
    </div>`;
  }
  html += `</div></div>`;

  const vendorAliases = (d.aliases.vendor || []);
  const otherAliases = Object.entries(d.aliases)
    .filter(([lang]) => lang !== 'vendor')
    .flatMap(([, names]) => names);

  if (vendorAliases.length || otherAliases.length) {
    html += `<div>
      <div class="sg-section-title">Known names &amp; aliases</div>
      <div class="sg-aliases">`;
    for (const a of vendorAliases) {
      html += `<span class="sg-alias-tag lang-vendor" title="Vendor name">${esc(a)}</span>`;
    }
    for (const a of otherAliases) {
      html += `<span class="sg-alias-tag">${esc(a)}</span>`;
    }
    html += `</div></div>`;
  }

  if (d.total_products > 0) {
    html += `<div><div class="sg-section-title">Available from vendors</div>`;
    for (const [cat, products] of Object.entries(d.products_by_cat)) {
      html += `<div class="sg-product-cat">
        <div class="sg-product-cat-name">${esc(cat)}</div>`;
      for (const p of products) {
        const stockClass = p.in_stock ? 'in-stock' : 'out-stock';
        const detail = [p.format, p.grade].filter(Boolean).join(' · ');
        html += `<div class="sg-product-row">
          <div class="sg-product-stock ${stockClass}" title="${p.in_stock ? 'In stock' : 'Out of stock'}"></div>
          <div class="sg-product-vendor">${p.vendor_flag} ${esc(p.vendor)}</div>
          ${detail ? `<div class="sg-product-format">${esc(detail)}</div>` : ''}
          <div class="sg-product-price">${p.price.toFixed(2)} ${p.currency}</div>
        </div>`;
      }
      html += `</div>`;
    }
    html += `</div>`;
  } else {
    html += `<div>
      <div class="sg-section-title">Availability</div>
      <p class="sg-unavailable-note">
        This species is not currently available from any vendor in the catalogue.
      </p>
    </div>`;
  }

  document.getElementById('sg-drawer-body').innerHTML = html;
}

function closeDrawer() {
  document.getElementById('sg-drawer-backdrop').classList.remove('is-open');
  if (sgState.activeId) {
    const card = document.getElementById(`sg-card-${sgState.activeId}`);
    if (card) card.classList.remove('is-active');
    sgState.activeId = null;
  }
}

// Wire events and boot — only on species page
if (document.getElementById('sg-grid')) {
  document.getElementById('sg-search').addEventListener('input', function() {
    clearTimeout(sgSearchTimer);
    sgSearchTimer = setTimeout(() => {
      sgState.q = this.value.trim();
      sgState.page = 1;
      loadGrid();
    }, 280);
  });

  document.querySelectorAll('.sg-filter-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      document.querySelectorAll('.sg-filter-btn').forEach(b => b.classList.remove('is-active'));
      this.classList.add('is-active');
      sgState.filter = this.dataset.filter;
      sgState.page = 1;
      loadGrid();
    });
  });

  document.getElementById('sg-drawer-close').addEventListener('click', closeDrawer);
  document.getElementById('sg-drawer-backdrop').addEventListener('click', function(e) {
    if (e.target === this) closeDrawer();
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeDrawer(); });

  loadGrid();
}