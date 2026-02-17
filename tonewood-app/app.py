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
    """Home page - shows all products with pagination"""
    try:
        from sqlalchemy import func

        sort_by    = request.args.get('sort', 'price')
        sort_order = request.args.get('order', 'asc')
        page       = request.args.get('page', 1, type=int)
        per_page   = 50

        # --- Dropdown data (all with counts, only species/vendors/cats that have products) ---
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
        formats_by_category = {}
        for cat, _ in categories:
            cat_formats = (
                db.session.query(Format, func.count(Product.product_id).label('cnt'))
                .join(Product, Product.format_id == Format.format_id)
                .filter(Product.category_id == cat.category_id)
                .group_by(Format.format_id)
                .order_by(Format.name)
                .all()
            )
            formats_by_category[cat.category_id] = cat_formats

        # --- Product query ---
        query = Product.query
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

        total_count = query.count()
        total_pages = max(1, (total_count + per_page - 1) // per_page)
        offset      = (page - 1) * per_page
        products    = query.offset(offset).limit(per_page).all()
        start_item  = offset + 1
        end_item    = min(offset + per_page, total_count)

        # --- Sort URL helper ---
        def sort_url(col):
            new_order = ('desc' if sort_order == 'asc' else 'asc') if sort_by == col else 'asc'
            icon = (' ↑' if sort_order == 'asc' else ' ↓') if sort_by == col else ''
            return f'/?sort={col}&order={new_order}&page=1', icon

        su, si = sort_url('species')
        vu, vi = sort_url('vendor')
        cu, ci = sort_url('category')
        fu, fi = sort_url('format')
        gu, gi = sort_url('grade')
        pu, pi = sort_url('price')

        # --- Pagination helper ---
        def pagination_html(base_url_prefix='/?'):
            pages_to_show = sorted(set(
                [1] +
                list(range(max(2, page - 2), min(total_pages, page + 3))) +
                ([total_pages] if total_pages > 1 else [])
            ))
            h = '<div class="pager">'
            prev_cls = 'page-btn' if page > 1 else 'page-btn disabled'
            prev_href = f'/?sort={sort_by}&order={sort_order}&page={page-1}' if page > 1 else '#'
            h += f'<a href="{prev_href}" class="{prev_cls}">← Prev</a>'
            prev_p = 0
            for p_ in pages_to_show:
                if p_ > prev_p + 1:
                    h += '<span class="page-ellipsis">…</span>'
                cls = 'page-num active' if p_ == page else 'page-num'
                h += f'<a href="/?sort={sort_by}&order={sort_order}&page={p_}" class="{cls}">{p_}</a>'
                prev_p = p_
            next_cls = 'page-btn' if page < total_pages else 'page-btn disabled'
            next_href = f'/?sort={sort_by}&order={sort_order}&page={page+1}' if page < total_pages else '#'
            h += f'<a href="{next_href}" class="{next_cls}">Next →</a>'
            h += '</div>'
            return h

        # ------------------------------------------------------------------ #
        #  HTML                                                                #
        # ------------------------------------------------------------------ #
        html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tonewood Prices</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #111113;
    color: #f4f4f5;
    min-height: 100vh;
    font-size: 14px;
  }

  /* ── Header ── */
  .header {
    background: #18181b;
    border-bottom: 1px solid #27272a;
    padding: 14px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 10;
  }
  .header-left { display: flex; align-items: center; gap: 12px; }
  .header-title { font-size: 15px; font-weight: 600; color: #f4f4f5; line-height: 1.2; }
  .header-sub   { font-size: 12px; color: #52525b; margin-top: 1px; }
  .toggle-btn {
    display: flex; align-items: center; gap: 6px;
    font-size: 13px; color: #71717a;
    background: #1c1c1e; border: 1px solid #2e2e32;
    border-radius: 6px; padding: 6px 12px; cursor: pointer;
    text-decoration: none;
  }
  .toggle-btn:hover { color: #f4f4f5; border-color: #52525b; }

  /* ── Layout ── */
  .main { max-width: 1400px; margin: 0 auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }

  /* ── Filter panel ── */
  .filter-panel {
    background: #18181b;
    border: 1px solid #27272a;
    border-radius: 8px;
    padding: 18px 20px;
  }
  .filter-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 14px;
  }
  .filter-group { display: flex; flex-direction: column; gap: 6px; }
  .filter-label {
    font-size: 11px; font-weight: 600; color: #6b7280;
    text-transform: uppercase; letter-spacing: 0.07em;
  }
  .filter-select, .filter-input {
    height: 36px;
    background: #1c1c1e;
    border: 1px solid #2e2e32;
    border-radius: 6px;
    color: #f4f4f5;
    font-size: 13px;
    padding: 0 28px 0 10px;
    width: 100%;
    appearance: none;
    -webkit-appearance: none;
    cursor: pointer;
    outline: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2352525b' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 9px center;
  }
  .filter-input { padding: 0 10px; background-image: none; }
  .filter-select:focus, .filter-input:focus { border-color: #52525b; }
  .filter-select option { background: #1c1c1e; color: #f4f4f5; }

  /* ── Results bar ── */
  .results-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 13px;
    color: #52525b;
  }
  .results-bar strong { color: #a1a1aa; font-weight: 600; }

  /* ── Table wrapper ── */
  .table-wrap {
    background: #18181b;
    border: 1px solid #27272a;
    border-radius: 8px;
    overflow: hidden;
  }
  .table-scroll { overflow-x: auto; }

  table { width: 100%; border-collapse: collapse; font-size: 13px; }

  thead th {
    background: #18181b;
    border-bottom: 1px solid #27272a;
    padding: 10px 16px;
    text-align: left;
    font-size: 11px;
    font-weight: 600;
    color: #52525b;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    white-space: nowrap;
    user-select: none;
  }
  thead th a {
    color: inherit;
    text-decoration: none;
    display: flex;
    align-items: center;
    gap: 3px;
  }
  thead th a:hover { color: #a1a1aa; }
  thead th.sorted a { color: #a1a1aa; }

  tbody tr { border-bottom: 1px solid #1f1f23; transition: background 0.1s; }
  tbody tr:last-child { border-bottom: none; }
  tbody tr:hover { background: #1c1c1e; }
  tbody td { padding: 11px 16px; vertical-align: middle; }

  .species-name  { font-weight: 500; color: #f4f4f5; }
  .species-alias { font-size: 11px; color: #52525b; margin-top: 2px; }
  .vendor-name   { color: #a1a1aa; white-space: nowrap; }
  .format-text   { color: #71717a; font-size: 12px; }
  .grade-text    { color: #71717a; font-size: 12px; }
  .price-val     { font-weight: 600; color: #f4f4f5; font-variant-numeric: tabular-nums; white-space: nowrap; }
  .price-cur     { color: #52525b; font-size: 11px; font-weight: 400; margin-left: 3px; }

  .view-link {
    display: inline-flex; align-items: center; gap: 3px;
    font-size: 12px; color: #71717a;
    border: 1px solid #2e2e32; border-radius: 4px;
    padding: 3px 8px; text-decoration: none;
    transition: color 0.1s, border-color 0.1s;
  }
  .view-link:hover { color: #f4f4f5; border-color: #52525b; }

  /* ── Table footer / pagination ── */
  .table-footer {
    border-top: 1px solid #27272a;
    padding: 10px 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #18181b;
  }
  .footer-count { font-size: 12px; color: #52525b; }

  .pager { display: flex; align-items: center; gap: 4px; }
  .page-btn, .page-num {
    height: 28px; min-width: 28px; padding: 0 8px;
    border-radius: 5px; font-size: 12px; font-weight: 400;
    color: #71717a; background: #1c1c1e;
    border: 1px solid #2e2e32;
    text-decoration: none; display: inline-flex; align-items: center; justify-content: center;
    transition: color 0.1s, border-color 0.1s, background 0.1s;
  }
  .page-btn:hover, .page-num:hover { color: #f4f4f5; border-color: #52525b; }
  .page-num.active { background: #27272a; color: #f4f4f5; border-color: #3f3f46; font-weight: 600; }
  .page-btn.disabled { color: #3f3f46; border-color: #27272a; pointer-events: none; background: transparent; }
  .page-ellipsis { color: #3f3f46; font-size: 12px; padding: 0 2px; }

  .no-results { padding: 60px 16px; text-align: center; color: #52525b; }
</style>
</head>
<body>

<!-- Header -->
<div class="header">
  <div class="header-left">
    <span style="font-size:22px;">🎸</span>
    <div>
      <div class="header-title">Tonewood Prices</div>
      <div class="header-sub">""" + str(len(vendors)) + """ vendors · """ + str(total_count) + """ products</div>
    </div>
  </div>
  <button class="toggle-btn" onclick="toggleFilters()">
    <span id="toggle-label">Hide filters</span> <span id="toggle-arrow">↑</span>
  </button>
</div>

<div class="main">

<!-- Filter panel -->
<div class="filter-panel" id="filter-panel">
  <form action="/search" method="get">
    <div class="filter-grid">

      <div class="filter-group">
        <label class="filter-label">Species</label>
        <select name="species_id" class="filter-select">
          <option value="">All species</option>
"""
        for s, cnt in species_list:
            display = s.commercial_name if s.commercial_name else s.scientific_name
            html += f'          <option value="{s.species_id}">{display} ({cnt})</option>\n'

        html += """        </select>
      </div>

      <div class="filter-group">
        <label class="filter-label">Vendor</label>
        <select name="vendor_id" class="filter-select">
          <option value="">All vendors</option>
"""
        for v, cnt in vendors:
            flag = VENDOR_FLAGS.get(v.country, '')
            html += f'          <option value="{v.vendor_id}">{v.name} · {v.country} {flag} ({cnt})</option>\n'

        html += """        </select>
      </div>

      <div class="filter-group">
        <label class="filter-label">Category</label>
        <select name="category_id" class="filter-select" id="category_select" onchange="updateFormatFilter()">
          <option value="">All categories</option>
"""
        for c, cnt in categories:
            html += f'          <option value="{c.category_id}">{c.name} ({cnt})</option>\n'

        html += """        </select>
      </div>

      <div class="filter-group" id="format_filter_group" style="display:none;">
        <label class="filter-label">Format</label>
        <select name="format_id" class="filter-select" id="format_select">
          <option value="">All formats</option>
        </select>
      </div>

      <div class="filter-group">
        <label class="filter-label">Max price (SEK)</label>
        <input type="number" name="max_price" placeholder="e.g. 500" class="filter-input">
      </div>

    </div><!-- /filter-grid -->

    <div style="margin-top:14px;padding-top:14px;border-top:1px solid #27272a;display:flex;align-items:center;gap:10px;">
      <button type="submit" style="height:34px;padding:0 18px;background:#27272a;border:1px solid #3f3f46;border-radius:6px;color:#f4f4f5;font-size:13px;cursor:pointer;font-weight:500;">
        Search
      </button>
      <a href="/" style="font-size:13px;color:#52525b;text-decoration:none;">Reset</a>
    </div>
  </form>
</div><!-- /filter-panel -->

<!-- Results bar -->
<div class="results-bar">
  <span>Showing <strong>""" + str(start_item) + """–""" + str(end_item) + """</strong> of <strong>""" + str(total_count) + """</strong> products</span>
</div>

<!-- Table -->
<div class="table-wrap">
  <div class="table-scroll">
  <table>
    <thead>
      <tr>
        <th class='""" + ('sorted' if sort_by=='species' else '') + f"""'><a href='{su}'>Species{si}</a></th>
        <th class='""" + ('sorted' if sort_by=='vendor' else '') + f"""'><a href='{vu}'>Vendor{vi}</a></th>
        <th class='""" + ('sorted' if sort_by=='category' else '') + f"""'><a href='{cu}'>Category{ci}</a></th>
        <th class='""" + ('sorted' if sort_by=='format' else '') + f"""'><a href='{fu}'>Format{fi}</a></th>
        <th class='""" + ('sorted' if sort_by=='grade' else '') + f"""'><a href='{gu}'>Grade{gi}</a></th>
        <th class='""" + ('sorted' if sort_by=='price' else '') + f"""'><a href='{pu}'>Price{pi}</a></th>
        <th>Updated</th>
        <th>Link</th>
      </tr>
    </thead>
    <tbody>
"""
        if not products:
            html += '<tr><td colspan="8" class="no-results">No products found.</td></tr>\n'
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

        html += """    </tbody>
  </table>
  </div><!-- /table-scroll -->
  <div class="table-footer">
    <span class="footer-count">""" + str(total_count) + """ products</span>
    """ + pagination_html() + """
  </div>
</div><!-- /table-wrap -->

</div><!-- /main -->

<script>
  const formatsByCategory = {
"""
        for cat_id, fmt_list in formats_by_category.items():
            items = []
            for f, cnt in fmt_list:
                safe = f.name.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")
                items.append(f'{{"id":{f.format_id},"name":"{safe} ({cnt})"}}')
            html += f'    "{cat_id}": [{",".join(items)}],\n'

        html += """  };

  function toggleFilters() {
    const panel = document.getElementById('filter-panel');
    const label = document.getElementById('toggle-label');
    const arrow = document.getElementById('toggle-arrow');
    const hidden = panel.style.display === 'none';
    panel.style.display = hidden ? 'block' : 'none';
    label.textContent = hidden ? 'Hide filters' : 'Show filters';
    arrow.textContent = hidden ? '↑' : '↓';
  }

  function updateFormatFilter() {
    const catId = document.getElementById('category_select').value;
    const group  = document.getElementById('format_filter_group');
    const select = document.getElementById('format_select');
    if (!catId) { group.style.display = 'none'; return; }
    group.style.display = 'flex';
    select.innerHTML = '<option value="">All formats</option>';
    (formatsByCategory[catId] || []).forEach(f => {
      const o = document.createElement('option');
      o.value = f.id; o.textContent = f.name;
      select.appendChild(o);
    });
  }
</script>
</body>
</html>"""

        return html

    except Exception as e:
        return f"<h1>Error</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>"
""" HOMEPAGE END """

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