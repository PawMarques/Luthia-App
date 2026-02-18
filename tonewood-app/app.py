from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
from models import db, Species, SpeciesAlias, Product, Vendor, Category, Grade, Format
import os
import traceback

app = Flask(__name__)

# Configure SQLite database
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "tonewood.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Create tables if they don't exist
with app.app_context():
    db.create_all()

""" HOMEPAGE START """

# Category badge styles (dark theme)
CATEGORY_STYLES = {
    'Body Blank':         {'bg': '#3b1f6e', 'text': '#c084fc', 'border': '#6d28d9'},
    'Neck Blank':         {'bg': '#1e3a5f', 'text': '#60a5fa', 'border': '#2563eb'},
    'Fretboard Blank':    {'bg': '#064e3b', 'text': '#34d399', 'border': '#059669'},
    'Top Blank':          {'bg': '#500724', 'text': '#f9a8d4', 'border': '#be185d'},
    'Carpentry lumber':   {'bg': '#1c1c1e', 'text': '#94a3b8', 'border': '#334155'},
    'Finished Fretboard': {'bg': '#042f2e', 'text': '#2dd4bf', 'border': '#0d9488'},
}

VENDOR_FLAGS = {
    'Sweden':   '🇸🇪',
    'Portugal': '🇵🇹',
    'Italy':    '🇮🇹',
    'Spain':    '🇪🇸',
}

def category_badge(name):
    s = CATEGORY_STYLES.get(name, {'bg': '#1c1c1e', 'text': '#94a3b8', 'border': '#334155'})
    return (f'<span style="display:inline-flex;align-items:center;font-size:11px;font-weight:500;'
            f'background:{s["bg"]};color:{s["text"]};border:1px solid {s["border"]};'
            f'border-radius:20px;padding:2px 8px;white-space:nowrap;">{name}</span>')

def staleness_cell(last_updated):
    """Return an HTML table cell with colour-coded last updated date."""
    if not last_updated:
        return '<td style="font-size:11px;color:#3f3f46;padding:11px 16px;">—</td>'
    now = datetime.utcnow()
    age_months = (now - last_updated).days / 30.4
    date_str = last_updated.strftime("%Y-%m-%d")
    if age_months <= 3:
        color = '#34d399'
    elif age_months <= 6:
        color = '#f59e0b'
    else:
        color = '#f87171'
    return f'<td style="font-size:11px;color:{color};padding:11px 16px;white-space:nowrap;">{date_str}</td>'




@app.route('/')
def index():
    """Home page — dropdown population only; products loaded live via /api/products"""
    try:
        from sqlalchemy import func

        species_list = (
            db.session.query(Species, func.count(Product.product_id).label('cnt'))
            .join(Product, Product.species_id == Species.species_id)
            .group_by(Species.species_id)
            .order_by(Species.commercial_name)
            .all()
        )
        vendors = (
            db.session.query(Vendor, func.count(Product.product_id).label('cnt'))
            .join(Product, Product.vendor_id == Vendor.vendor_id)
            .filter(Vendor.active == True)
            .group_by(Vendor.vendor_id)
            .order_by(Vendor.name)
            .all()
        )
        categories = (
            db.session.query(Category, func.count(Product.product_id).label('cnt'))
            .join(Product, Product.category_id == Category.category_id)
            .group_by(Category.category_id)
            .order_by(Category.name)
            .all()
        )
        total_products = Product.query.count()

        species_opts = '<option value="">All species</option>\n'
        for s, cnt in species_list:
            display = s.commercial_name or s.scientific_name
            species_opts += f'<option value="{s.species_id}">{display} ({cnt})</option>\n'

        vendor_opts = '<option value="">All vendors</option>\n'
        for v, cnt in vendors:
            flag = VENDOR_FLAGS.get(v.country, '')
            vendor_opts += f'<option value="{v.vendor_id}">{v.name} · {v.country} {flag} ({cnt})</option>\n'

        cat_opts = '<option value="">All categories</option>\n'
        for c, cnt in categories:
            cat_opts += f'<option value="{c.category_id}" data-name="{c.name}">{c.name} ({cnt})</option>\n'

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tonewood Prices</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #111113; color: #f4f4f5; min-height: 100vh; font-size: 14px;
  }}
  .header {{
    background: #18181b; border-bottom: 1px solid #27272a;
    padding: 14px 24px; display: flex; align-items: center;
    justify-content: space-between; position: sticky; top: 0; z-index: 10;
  }}
  .header-left {{ display: flex; align-items: center; gap: 12px; }}
  .header-title {{ font-size: 15px; font-weight: 600; color: #f4f4f5; }}
  .header-sub   {{ font-size: 12px; color: #52525b; margin-top: 2px; }}
  .toggle-btn {{
    font-size: 13px; color: #71717a; background: #1c1c1e;
    border: 1px solid #2e2e32; border-radius: 6px; padding: 6px 12px; cursor: pointer;
  }}
  .toggle-btn:hover {{ color: #f4f4f5; border-color: #52525b; }}
  .main {{ max-width: 1400px; margin: 0 auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }}
  .filter-panel {{ background: #18181b; border: 1px solid #27272a; border-radius: 8px; padding: 18px 20px; }}
  .filter-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; align-items: end; }}
  .filter-group {{ display: flex; flex-direction: column; gap: 6px; }}
  .filter-label {{ font-size: 11px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.07em; }}
  .filter-select, .filter-input {{
    height: 36px; background: #1c1c1e; border: 1px solid #2e2e32; border-radius: 6px;
    color: #f4f4f5; font-size: 13px; padding: 0 28px 0 10px; width: 100%;
    appearance: none; -webkit-appearance: none; cursor: pointer; outline: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2352525b' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
    background-repeat: no-repeat; background-position: right 9px center;
    transition: border-color 0.15s;
  }}
  .filter-input {{ padding: 0 10px; background-image: none; }}
  .filter-select:focus, .filter-input:focus {{ border-color: #52525b; }}
  .filter-select option {{ background: #1c1c1e; color: #f4f4f5; }}
  .filter-select.has-value, .filter-input.has-value {{ border-color: #3f3f46; }}
  .chips-row {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; min-height: 28px; }}
  .chip {{
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 12px; color: #a1a1aa;
    background: #27272a; border: 1px solid #3f3f46; border-radius: 20px;
    padding: 3px 10px;
  }}
  .chip-x {{ font-size: 14px; color: #52525b; cursor: pointer; line-height: 1; padding: 0 0 0 2px; }}
  .chip-x:hover {{ color: #f4f4f5; }}
  .chips-clear {{
    font-size: 12px; color: #52525b; cursor: pointer;
    background: none; border: none; padding: 0; margin-left: 4px;
  }}
  .chips-clear:hover {{ color: #a1a1aa; }}
  .results-bar {{ display: flex; align-items: center; justify-content: space-between; font-size: 13px; color: #52525b; }}
  .results-bar strong {{ color: #a1a1aa; }}
  .table-wrap {{ background: #18181b; border: 1px solid #27272a; border-radius: 8px; overflow: hidden; }}
  .table-scroll {{ overflow-x: auto; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  thead th {{
    background: #18181b; border-bottom: 1px solid #27272a;
    padding: 10px 16px; text-align: left; font-size: 11px; font-weight: 600;
    color: #52525b; text-transform: uppercase; letter-spacing: 0.07em;
    white-space: nowrap; user-select: none; cursor: pointer;
  }}
  thead th:hover {{ color: #a1a1aa; }}
  thead th.sorted {{ color: #a1a1aa; }}
  tbody tr {{ border-bottom: 1px solid #1f1f23; transition: background 0.1s; }}
  tbody tr:last-child {{ border-bottom: none; }}
  tbody tr:hover {{ background: #1c1c1e; }}
  tbody td {{ padding: 11px 16px; vertical-align: middle; }}
  .species-name  {{ font-weight: 500; color: #f4f4f5; }}
  .species-alias {{ font-size: 11px; color: #52525b; margin-top: 2px; }}
  .vendor-name   {{ color: #a1a1aa; white-space: nowrap; }}
  .dim           {{ color: #71717a; font-size: 12px; }}
  .price-val     {{ font-weight: 600; color: #f4f4f5; font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .price-cur     {{ color: #52525b; font-size: 11px; margin-left: 3px; }}
  .view-link {{
    display: inline-flex; align-items: center; gap: 3px; font-size: 12px; color: #71717a;
    border: 1px solid #2e2e32; border-radius: 4px; padding: 3px 8px; text-decoration: none;
    transition: color 0.1s, border-color 0.1s;
  }}
  .view-link:hover {{ color: #f4f4f5; border-color: #52525b; }}
  .table-footer {{
    border-top: 1px solid #27272a; padding: 10px 16px;
    display: flex; align-items: center; justify-content: space-between; background: #18181b;
  }}
  .footer-count {{ font-size: 12px; color: #52525b; }}
  .pager {{ display: flex; align-items: center; gap: 4px; }}
  .page-btn, .page-num {{
    height: 28px; min-width: 28px; padding: 0 8px; border-radius: 5px;
    font-size: 12px; color: #71717a; background: #1c1c1e; border: 1px solid #2e2e32;
    cursor: pointer; display: inline-flex; align-items: center; justify-content: center;
    transition: color 0.1s, border-color 0.1s, background 0.1s;
  }}
  .page-btn:hover, .page-num:hover {{ color: #f4f4f5; border-color: #52525b; }}
  .page-num.active {{ background: #27272a; color: #f4f4f5; border-color: #3f3f46; font-weight: 600; }}
  .page-btn:disabled {{ color: #3f3f46; border-color: #27272a; pointer-events: none; background: transparent; }}
  .page-ellipsis {{ color: #3f3f46; font-size: 12px; padding: 0 2px; }}
  .loading-row td {{ padding: 14px 16px; }}
  .shimmer {{
    height: 14px; border-radius: 4px;
    background: linear-gradient(90deg,#1f1f23 25%,#27272a 50%,#1f1f23 75%);
    background-size: 200% 100%; animation: shimmer 1.2s infinite;
  }}
  @keyframes shimmer {{ 0%{{background-position:200% 0}} 100%{{background-position:-200% 0}} }}
  .no-results {{ padding: 60px 16px; text-align: center; color: #52525b; }}
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <span style="font-size:22px;">🎸</span>
    <div>
      <div class="header-title">Tonewood Prices</div>
      <div class="header-sub">{len(vendors)} vendors · {total_products} products</div>
    </div>
  </div>
  <button class="toggle-btn" onclick="toggleFilters()">
    <span id="toggle-label">Hide filters</span> <span id="toggle-arrow">↑</span>
  </button>
</div>

<div class="main">

<div class="filter-panel" id="filter-panel">
  <div class="filter-grid">
    <div class="filter-group">
      <label class="filter-label">Species</label>
      <select id="f-species" class="filter-select" onchange="onFilterChange('species')">
        {species_opts}
      </select>
    </div>
    <div class="filter-group">
      <label class="filter-label">Vendor</label>
      <select id="f-vendor" class="filter-select" onchange="onFilterChange('vendor')">
        {vendor_opts}
      </select>
    </div>
    <div class="filter-group">
      <label class="filter-label">Category</label>
      <select id="f-category" class="filter-select" onchange="onFilterChange('category')">
        {cat_opts}
      </select>
    </div>
    <div class="filter-group" id="format-group" style="display:none;">
      <label class="filter-label">Format</label>
      <select id="f-format" class="filter-select" onchange="onFilterChange('format')">
        <option value="">All formats</option>
      </select>
    </div>
    <div class="filter-group">
      <label class="filter-label">Max price (SEK)</label>
      <input type="number" id="f-price" class="filter-input" placeholder="e.g. 500" oninput="onPriceInput()">
    </div>
  </div>
</div>

<div class="chips-row" id="chips-row"></div>

<div class="results-bar">
  <span id="results-text">Loading…</span>
</div>

<div class="table-wrap">
  <div class="table-scroll">
  <table>
    <thead>
      <tr>
        <th data-col="species"  onclick="sortBy('species')" >Species</th>
        <th data-col="vendor"   onclick="sortBy('vendor')"  >Vendor</th>
        <th data-col="category" onclick="sortBy('category')">Category</th>
        <th data-col="format"   onclick="sortBy('format')"  >Format</th>
        <th data-col="grade"    onclick="sortBy('grade')"   >Grade</th>
        <th data-col="price"    onclick="sortBy('price')"   >Price</th>
        <th>Updated</th>
        <th>Link</th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
  </div>
  <div class="table-footer">
    <span class="footer-count" id="footer-count"></span>
    <div class="pager" id="pager"></div>
  </div>
</div>

</div>

<script>
const state = {{
  species_id: null, vendor_id: null, category_id: null,
  format_id: null, max_price: null,
  sort: 'price', order: 'asc', page: 1,
}};
const labels = {{}};

function esc(s) {{
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}
function setHasValue(id, val) {{
  const el = document.getElementById(id);
  if (el) el.classList.toggle('has-value', !!val);
}}

function onFilterChange(key) {{
  const ids = {{ species:'f-species', vendor:'f-vendor', category:'f-category', format:'f-format' }};
  const sel = document.getElementById(ids[key]);
  const val = sel.value ? parseInt(sel.value) : null;
  state[key + '_id'] = val;
  state.page = 1;
  setHasValue(ids[key], val);
  if (val) labels[key] = sel.options[sel.selectedIndex].text.replace(/ [(][0-9]+[)]$/, '');
  else     delete labels[key];
  if (key === 'category') {{
    state.format_id = null;
    delete labels.format;
    const ff = document.getElementById('f-format');
    if (ff) {{ ff.value = ''; setHasValue('f-format', false); }}
    document.getElementById('format-group').style.display = val ? 'flex' : 'none';
  }}
  fetchAndRender();
}}

let priceTimer = null;
function onPriceInput() {{
  clearTimeout(priceTimer);
  priceTimer = setTimeout(() => {{
    const val = document.getElementById('f-price').value;
    state.max_price = val ? parseFloat(val) : null;
    state.page = 1;
    setHasValue('f-price', state.max_price);
    if (state.max_price) labels.price = '≤ ' + Math.round(state.max_price) + ' SEK';
    else delete labels.price;
    fetchAndRender();
  }}, 400);
}}

function sortBy(col) {{
  state.order = (state.sort === col && state.order === 'asc') ? 'desc' : 'asc';
  state.sort = col;
  state.page = 1;
  fetchAndRender();
}}

function goToPage(p) {{
  state.page = p;
  fetchAndRender();
  window.scrollTo({{ top: 0, behavior: 'smooth' }});
}}

function clearFilter(key) {{
  const ids = {{ species:'f-species', vendor:'f-vendor', category:'f-category', format:'f-format', price:'f-price' }};
  if (key === 'price') state.max_price = null;
  else state[key + '_id'] = null;
  delete labels[key];
  const el = document.getElementById(ids[key]);
  if (el) {{ el.value = ''; setHasValue(ids[key], false); }}
  if (key === 'category') {{
    state.format_id = null; delete labels.format;
    const ff = document.getElementById('f-format');
    if (ff) {{ ff.value = ''; setHasValue('f-format', false); }}
    document.getElementById('format-group').style.display = 'none';
  }}
  state.page = 1;
  fetchAndRender();
}}

function clearAll() {{
  ['species','vendor','category','format'].forEach(k => {{
    state[k+'_id'] = null;
    const el = document.getElementById('f-'+k);
    if (el) {{ el.value=''; setHasValue('f-'+k, false); }}
  }});
  state.max_price = null;
  const fp = document.getElementById('f-price');
  if (fp) {{ fp.value=''; setHasValue('f-price', false); }}
  document.getElementById('format-group').style.display = 'none';
  Object.keys(labels).forEach(k => delete labels[k]);
  state.page = 1;
  fetchAndRender();
}}

function renderChips() {{
  const row = document.getElementById('chips-row');
  const active = Object.entries(labels);
  if (!active.length) {{ row.innerHTML = ''; return; }}
  let html = active.map(([k,l]) =>
    `<span class="chip">${{esc(l)}}<span class="chip-x" onclick="clearFilter('${{k}}')">×</span></span>`
  ).join('');
  if (active.length > 1) html += `<button class="chips-clear" onclick="clearAll()">Clear all</button>`;
  row.innerHTML = html;
}}

function updateSortHeaders() {{
  document.querySelectorAll('thead th[data-col]').forEach(th => {{
    const col = th.dataset.col;
    const base = col.charAt(0).toUpperCase() + col.slice(1);
    if (state.sort === col) {{
      th.classList.add('sorted');
      th.textContent = base + (state.order === 'asc' ? ' ↑' : ' ↓');
    }} else {{
      th.classList.remove('sorted');
      th.textContent = base;
    }}
  }});
}}

function renderRows(rows) {{
  const tbody = document.getElementById('tbody');
  if (!rows.length) {{
    tbody.innerHTML = '<tr><td colspan="8" class="no-results">No products match your filters.</td></tr>';
    return;
  }}
  tbody.innerHTML = rows.map(p => `<tr>
    <td>
      <div class="species-name">${{esc(p.species)}}</div>
      ${{p.alias ? `<div class="species-alias">listed as: ${{esc(p.alias)}}</div>` : ''}}
    </td>
    <td class="vendor-name">${{esc(p.vendor)}} ${{p.vendor_flag}}</td>
    <td><span style="display:inline-flex;align-items:center;font-size:11px;font-weight:500;
      background:${{p.cat_bg}};color:${{p.cat_text}};border:1px solid ${{p.cat_border}};
      border-radius:20px;padding:2px 8px;white-space:nowrap;">${{esc(p.category)}}</span></td>
    <td class="dim">${{esc(p.format || '—')}}</td>
    <td class="dim">${{esc(p.grade  || '—')}}</td>
    <td><span class="price-val">${{p.price.toFixed(2)}}</span><span class="price-cur">SEK</span></td>
    <td style="font-size:11px;color:${{p.stale_color}};white-space:nowrap;">${{p.stale_date || '—'}}</td>
    <td>${{p.url ? `<a href="${{esc(p.url)}}" target="_blank" class="view-link">View ↗</a>` : '<span class="dim">—</span>'}}</td>
  </tr>`).join('');
}}

function renderPager(page, pages) {{
  const pager = document.getElementById('pager');
  if (pages <= 1) {{ pager.innerHTML = ''; return; }}
  const toShow = new Set([1, pages]);
  for (let p = Math.max(2,page-2); p <= Math.min(pages-1,page+2); p++) toShow.add(p);
  const sorted = [...toShow].sort((a,b)=>a-b);
  let html = `<button class="page-btn" onclick="goToPage(${{page-1}})" ${{page===1?'disabled':''}}>← Prev</button>`;
  let prev = 0;
  for (const p of sorted) {{
    if (p > prev+1) html += '<span class="page-ellipsis">…</span>';
    html += `<button class="page-num${{p===page?' active':''}}" onclick="goToPage(${{p}})">${{p}}</button>`;
    prev = p;
  }}
  html += `<button class="page-btn" onclick="goToPage(${{page+1}})" ${{page===pages?'disabled':''}}>Next →</button>`;
  pager.innerHTML = html;
}}

function updateFormatDropdown(formats) {{
  const group = document.getElementById('format-group');
  const select = document.getElementById('f-format');
  if (!formats || !formats.length) {{ group.style.display = 'none'; return; }}
  group.style.display = 'flex';
  select.innerHTML = '<option value="">All formats</option>' +
    formats.map(f => `<option value="${{f.id}}"${{f.id===state.format_id?' selected':''}}>${{esc(f.name)}} (${{f.count}})</option>`).join('');
}}

function showLoading() {{
  document.getElementById('tbody').innerHTML = Array(8).fill(`<tr class="loading-row">
    ${{Array(8).fill('<td><div class="shimmer"></div></td>').join('')}}
  </tr>`).join('');
}}

function toggleFilters() {{
  const panel = document.getElementById('filter-panel');
  const label = document.getElementById('toggle-label');
  const arrow = document.getElementById('toggle-arrow');
  const hidden = panel.style.display === 'none';
  panel.style.display = hidden ? 'block' : 'none';
  label.textContent = hidden ? 'Hide filters' : 'Show filters';
  arrow.textContent = hidden ? '↑' : '↓';
}}

function fetchAndRender() {{
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
    .then(data => {{
      renderRows(data.rows);
      renderPager(data.page, data.pages);
      const start = (data.page-1)*50+1, end = Math.min(data.page*50, data.total);
      document.getElementById('results-text').innerHTML =
        `Showing <strong>${{start}}–${{end}}</strong> of <strong>${{data.total}}</strong> products`;
      document.getElementById('footer-count').textContent = data.total + ' products';
      if (state.category_id) updateFormatDropdown(data.formats);
    }})
    .catch(() => {{
      document.getElementById('tbody').innerHTML =
        '<tr><td colspan="8" class="no-results">Error loading products.</td></tr>';
    }});
}}

fetchAndRender();
</script>
</body>
</html>"""

    except Exception as e:
        return f"<h1>Error</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>"

""" API START """
@app.route('/api/products')
def api_products():
    """JSON endpoint for live filtering"""
    from sqlalchemy import func

    species_id  = request.args.get('species_id',  type=int)
    vendor_id   = request.args.get('vendor_id',   type=int)
    category_id = request.args.get('category_id', type=int)
    format_id   = request.args.get('format_id',   type=int)
    max_price   = request.args.get('max_price',   type=float)
    sort_by     = request.args.get('sort',  'price')
    sort_order  = request.args.get('order', 'asc')
    page        = request.args.get('page',  1, type=int)
    per_page    = 50

    query = Product.query
    if species_id:  query = query.filter_by(species_id=species_id)
    if vendor_id:   query = query.filter_by(vendor_id=vendor_id)
    if category_id: query = query.filter_by(category_id=category_id)
    if format_id:   query = query.filter_by(format_id=format_id)
    if max_price:   query = query.filter(Product.price <= max_price)

    if sort_by == 'species':
        query = query.join(Species).order_by(Species.commercial_name.asc() if sort_order == 'asc' else Species.commercial_name.desc())
    elif sort_by == 'vendor':
        query = query.join(Vendor).order_by(Vendor.name.asc() if sort_order == 'asc' else Vendor.name.desc())
    elif sort_by == 'category':
        query = query.join(Category).order_by(Category.name.asc() if sort_order == 'asc' else Category.name.desc())
    elif sort_by == 'grade':
        query = query.outerjoin(Grade).order_by(Grade.name.asc() if sort_order == 'asc' else Grade.name.desc())
    elif sort_by == 'format':
        query = query.outerjoin(Format).order_by(Format.name.asc() if sort_order == 'asc' else Format.name.desc())
    else:
        query = query.order_by(Product.price.asc() if sort_order == 'asc' else Product.price.desc())

    total = query.count()
    products = query.offset((page - 1) * per_page).limit(per_page).all()

    # Also return available formats for the selected category (for dynamic format dropdown)
    formats = []
    if category_id:
        fmt_rows = (
            db.session.query(Format, func.count(Product.product_id).label('cnt'))
            .join(Product, Product.format_id == Format.format_id)
            .filter(Product.category_id == category_id)
            .group_by(Format.format_id)
            .order_by(Format.name)
            .all()
        )
        formats = [{'id': f.format_id, 'name': f.name, 'count': cnt} for f, cnt in fmt_rows]

    rows = []
    for p in products:
        display_name = p.species.commercial_name or p.species.scientific_name
        listed = p.species_as_listed or ''
        alias = listed if (listed and listed.lower() != display_name.lower()
                           and listed.lower() != p.species.scientific_name.lower()) else ''
        cat = p.category.name
        s = CATEGORY_STYLES.get(cat, {'bg': '#1c1c1e', 'text': '#94a3b8', 'border': '#334155'})
        flag = VENDOR_FLAGS.get(p.vendor.country, '')

        # Staleness colour
        stale_color = '#3f3f46'
        stale_date  = ''
        if p.last_updated:
            age_months = (datetime.utcnow() - p.last_updated).days / 30.4
            stale_date = p.last_updated.strftime('%Y-%m-%d')
            stale_color = '#34d399' if age_months <= 3 else ('#f59e0b' if age_months <= 6 else '#f87171')

        rows.append({
            'species':     display_name,
            'alias':       alias,
            'vendor':      p.vendor.name,
            'vendor_flag': flag,
            'category':    cat,
            'cat_bg':      s['bg'],
            'cat_text':    s['text'],
            'cat_border':  s['border'],
            'format':      p.format.name if p.format else '',
            'grade':       p.grade.name  if p.grade  else '',
            'price':       round(p.price, 2),
            'url':         p.product_url or '',
            'stale_date':  stale_date,
            'stale_color': stale_color,
        })

    return jsonify({
        'total':   total,
        'page':    page,
        'pages':   max(1, (total + per_page - 1) // per_page),
        'rows':    rows,
        'formats': formats,
    })
""" API END """

""" SEARCH START """
@app.route('/search')
def search():
    """Search products with filters"""
    species_id  = request.args.get('species_id',  type=int)
    vendor_id   = request.args.get('vendor_id',   type=int)
    category_id = request.args.get('category_id', type=int)
    format_id   = request.args.get('format_id',   type=int)
    max_price   = request.args.get('max_price',   type=float)
    sort_by     = request.args.get('sort',  'price')
    sort_order  = request.args.get('order', 'asc')

    query = Product.query
    if species_id:  query = query.filter_by(species_id=species_id)
    if vendor_id:   query = query.filter_by(vendor_id=vendor_id)
    if category_id: query = query.filter_by(category_id=category_id)
    if format_id:   query = query.filter_by(format_id=format_id)
    if max_price:   query = query.filter(Product.price <= max_price)

    if sort_by == 'species':
        query = query.join(Species).order_by(Species.commercial_name.asc() if sort_order == 'asc' else Species.commercial_name.desc())
    elif sort_by == 'vendor':
        query = query.join(Vendor).order_by(Vendor.name.asc() if sort_order == 'asc' else Vendor.name.desc())
    elif sort_by == 'category':
        query = query.join(Category).order_by(Category.name.asc() if sort_order == 'asc' else Category.name.desc())
    elif sort_by == 'grade':
        query = query.outerjoin(Grade).order_by(Grade.name.asc() if sort_order == 'asc' else Grade.name.desc())
    elif sort_by == 'format':
        query = query.outerjoin(Format).order_by(Format.name.asc() if sort_order == 'asc' else Format.name.desc())
    else:
        query = query.order_by(Product.price.asc() if sort_order == 'asc' else Product.price.desc())

    products = query.all()

    def sort_url(col):
        new_order = ('desc' if sort_order == 'asc' else 'asc') if sort_by == col else 'asc'
        icon = (' ↑' if sort_order == 'asc' else ' ↓') if sort_by == col else ''
        params = []
        if species_id:  params.append(f'species_id={species_id}')
        if vendor_id:   params.append(f'vendor_id={vendor_id}')
        if category_id: params.append(f'category_id={category_id}')
        if format_id:   params.append(f'format_id={format_id}')
        if max_price:   params.append(f'max_price={max_price}')
        params += [f'sort={col}', f'order={new_order}']
        return f'/search?{"&".join(params)}', icon

    su, si = sort_url('species')
    vu, vi = sort_url('vendor')
    cu, ci = sort_url('category')
    fu, fi = sort_url('format')
    gu, gi = sort_url('grade')
    pu, pi = sort_url('price')

    # Active filter labels
    filter_chips = []
    if species_id:
        sp = Species.query.get(species_id)
        if sp: filter_chips.append(sp.commercial_name or sp.scientific_name)
    if vendor_id:
        v = Vendor.query.get(vendor_id)
        if v: filter_chips.append(v.name)
    if category_id:
        c = Category.query.get(category_id)
        if c: filter_chips.append(c.name)
    if format_id:
        f = Format.query.get(format_id)
        if f: filter_chips.append(f.name)
    if max_price:
        filter_chips.append(f'≤ {max_price:.0f} SEK')

    chips_html = ' '.join(
        f'<span style="display:inline-flex;align-items:center;gap:4px;font-size:12px;color:#a1a1aa;background:#27272a;border:1px solid #3f3f46;border-radius:20px;padding:2px 10px;">{c}</span>'
        for c in filter_chips
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Search Results – Tonewood</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #111113; color: #f4f4f5; min-height: 100vh; font-size: 14px; }}
  .header {{ background: #18181b; border-bottom: 1px solid #27272a; padding: 14px 24px; display: flex; align-items: center; justify-content: space-between; }}
  .back-link {{ font-size: 13px; color: #71717a; text-decoration: none; display: flex; align-items: center; gap: 6px; border: 1px solid #2e2e32; border-radius: 6px; padding: 6px 12px; background: #1c1c1e; }}
  .back-link:hover {{ color: #f4f4f5; border-color: #52525b; }}
  .header-right {{ font-size: 12px; color: #52525b; }}
  .main {{ max-width: 1400px; margin: 0 auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }}
  .results-bar {{ display: flex; align-items: center; justify-content: space-between; font-size: 13px; color: #52525b; flex-wrap: wrap; gap: 8px; }}
  .results-bar strong {{ color: #a1a1aa; font-weight: 600; }}
  .table-wrap {{ background: #18181b; border: 1px solid #27272a; border-radius: 8px; overflow: hidden; }}
  .table-scroll {{ overflow-x: auto; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  thead th {{ background: #18181b; border-bottom: 1px solid #27272a; padding: 10px 16px; text-align: left; font-size: 11px; font-weight: 600; color: #52525b; text-transform: uppercase; letter-spacing: 0.07em; white-space: nowrap; user-select: none; }}
  thead th a {{ color: inherit; text-decoration: none; display: flex; align-items: center; gap: 3px; }}
  thead th a:hover {{ color: #a1a1aa; }}
  thead th.sorted a {{ color: #a1a1aa; }}
  tbody tr {{ border-bottom: 1px solid #1f1f23; transition: background 0.1s; }}
  tbody tr:last-child {{ border-bottom: none; }}
  tbody tr:hover {{ background: #1c1c1e; }}
  tbody td {{ padding: 11px 16px; vertical-align: middle; }}
  .species-name {{ font-weight: 500; color: #f4f4f5; }}
  .species-alias {{ font-size: 11px; color: #52525b; margin-top: 2px; }}
  .vendor-name {{ color: #a1a1aa; white-space: nowrap; }}
  .format-text, .grade-text {{ color: #71717a; font-size: 12px; }}
  .price-val {{ font-weight: 600; color: #f4f4f5; font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .price-cur {{ color: #52525b; font-size: 11px; font-weight: 400; margin-left: 3px; }}
  .view-link {{ display: inline-flex; align-items: center; gap: 3px; font-size: 12px; color: #71717a; border: 1px solid #2e2e32; border-radius: 4px; padding: 3px 8px; text-decoration: none; transition: color 0.1s, border-color 0.1s; }}
  .view-link:hover {{ color: #f4f4f5; border-color: #52525b; }}
  .no-results {{ padding: 60px 16px; text-align: center; color: #52525b; }}
  .table-footer {{ border-top: 1px solid #27272a; padding: 10px 16px; display: flex; align-items: center; justify-content: between; background: #18181b; }}
  .footer-count {{ font-size: 12px; color: #52525b; }}
</style>
</head>
<body>

<div class="header">
  <a href="/" class="back-link">← Back</a>
  <span class="header-right">🎸 Tonewood Prices</span>
</div>

<div class="main">

  <div class="results-bar">
    <span>
      <strong>{len(products)}</strong> result{"s" if len(products) != 1 else ""}
      {f"&nbsp;·&nbsp; {chips_html}" if chips_html else ""}
    </span>
    <a href="/" style="font-size:12px;color:#52525b;text-decoration:none;">Clear filters</a>
  </div>

  <div class="table-wrap">
    <div class="table-scroll">
    <table>
      <thead>
        <tr>
          <th class='{"sorted" if sort_by=="species" else ""}'><a href='{su}'>Species{si}</a></th>
          <th class='{"sorted" if sort_by=="vendor" else ""}'><a href='{vu}'>Vendor{vi}</a></th>
          <th class='{"sorted" if sort_by=="category" else ""}'><a href='{cu}'>Category{ci}</a></th>
          <th class='{"sorted" if sort_by=="format" else ""}'><a href='{fu}'>Format{fi}</a></th>
          <th class='{"sorted" if sort_by=="grade" else ""}'><a href='{gu}'>Grade{gi}</a></th>
          <th class='{"sorted" if sort_by=="price" else ""}'><a href='{pu}'>Price{pi}</a></th>
          <th>Updated</th>
          <th>Link</th>
        </tr>
      </thead>
      <tbody>
"""
    if not products:
        html += '<tr><td colspan="8" class="no-results">No products match your filters.</td></tr>\n'
    else:
        for p in products:
            display_name = p.species.commercial_name or p.species.scientific_name
            listed = p.species_as_listed or ''
            alias_html = ''
            if listed and listed.lower() != display_name.lower() and listed.lower() != p.species.scientific_name.lower():
                alias_html = f'<div class="species-alias">listed as: {listed}</div>'
            grade_text  = p.grade.name  if p.grade  else '—'
            format_text = p.format.name if p.format else '—'
            flag = VENDOR_FLAGS.get(p.vendor.country, '')
            html += f"""      <tr>
        <td><div class="species-name">{display_name}</div>{alias_html}</td>
        <td class="vendor-name">{p.vendor.name} {flag}</td>
        <td>{category_badge(p.category.name)}</td>
        <td class="format-text">{format_text}</td>
        <td class="grade-text">{grade_text}</td>
        <td><span class="price-val">{p.price:.2f}</span><span class="price-cur">SEK</span></td>
        {staleness_cell(p.last_updated)}
        <td><a href="{p.product_url or '#'}" target="_blank" class="view-link">View ↗</a></td>
      </tr>\n"""

    html += f"""      </tbody>
    </table>
    </div>
    <div class="table-footer">
      <span class="footer-count">{len(products)} products</span>
    </div>
  </div>

</div>
</body>
</html>"""

    return html
""" SEARCH END """

if __name__ == '__main__':
    print("\n" + "="*50)
    print("Tonewood Price Comparison is starting...")
    print("Open your browser and go to: http://localhost:5000")
    print("Press CTRL+C to stop the server")
    print("="*50 + "\n")
    app.run(debug=True, port=5000)