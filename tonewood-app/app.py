from flask import Flask, render_template, request, jsonify, send_from_directory
from datetime import datetime, timedelta
from models import db, Species, SpeciesAlias, Product, Vendor, Category, Grade, Format, ProductImage
import os
import uuid
import traceback

app = Flask(__name__)

# Configure SQLite database
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "tonewood.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Upload folder for product images
UPLOAD_FOLDER = os.path.join(basedir, 'static', 'product-images')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
  <title>Tonewood Finder</title>
  <link rel="stylesheet" href="/static/tonewood-dark.css">
</head>
<body>

<div class="header">
  <div class="header-top">
    <div class="header-left">
      <span>🎸</span>
      <div>
        <div class="header-title">Tonewood Finder</div>
        <div class="header-sub">{len(vendors)} vendors · {total_products} products</div>
      </div>
    </div>
    <button class="toggle-btn" onclick="toggleFilters()">
      <span id="toggle-label">Hide filters</span> <span id="toggle-arrow">↑</span>
    </button>
  </div>

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
    <div class="chips-row" id="chips-row"></div>
  </div>
</div>

<div class="main">

  <div class="results-bar">
    <span id="results-text">Loading…</span>
    <div class="pager" id="pager-top"></div>
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
<script src="/static/tonewood-app.js" type="text/javascript"></script>
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
            'product_id':  p.product_id,
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

@app.route('/api/products/<int:product_id>')
def api_product_detail(product_id):
    """Full detail for a single product, plus species names and sibling listings."""
    p = Product.query.get_or_404(product_id)
    sp = p.species

    def stale_info(dt):
        if not dt:
            return '', '#3f3f46'
        age = (datetime.utcnow() - dt).days / 30.4
        color = '#34d399' if age <= 3 else ('#f59e0b' if age <= 6 else '#f87171')
        return dt.strftime('%Y-%m-%d'), color

    stale_date, stale_color = stale_info(p.last_updated)

    # All aliases grouped by language
    aliases = {}
    for a in sp.aliases:
        lang = a.language or 'other'
        aliases.setdefault(lang, [])
        if a.alias_name not in aliases[lang]:
            aliases[lang].append(a.alias_name)

    # Sibling listings removed

    cat = p.category.name
    cs  = CATEGORY_STYLES.get(cat, {'bg': '#1c1c1e', 'text': '#94a3b8', 'border': '#334155'})

    return jsonify({
        'product_id':          p.product_id,
        'price':               round(p.price, 2),
        'currency':            p.currency or 'SEK',
        'in_stock':            p.in_stock,
        'species_as_listed':   p.species_as_listed or '',
        'thickness_mm':        p.thickness_mm,
        'width_mm':            p.width_mm,
        'length_mm':           p.length_mm,
        'weight_kg':           p.weight_kg,
        'url':                 p.product_url or '',
        'stale_date':          stale_date,
        'stale_color':         stale_color,
        'dimensions':          _fmt_dims(p),
        'category':            cat,
        'cat_bg':  cs['bg'], 'cat_text': cs['text'], 'cat_border': cs['border'],
        'format':              p.format.name if p.format else '',
        'grade':               p.grade.name  if p.grade  else '',
        'unit':                p.unit.name   if p.unit   else '',
        'vendor':              p.vendor.name,
        'vendor_flag':         VENDOR_FLAGS.get(p.vendor.country, ''),
        'vendor_country':      p.vendor.country or '',
        'vendor_website':      p.vendor.website or '',
        'vendor_currency':     p.vendor.currency or '',
        'scientific_name':     sp.scientific_name or '',
        'commercial_name':     sp.commercial_name or '',
        'alt_commercial_name': sp.alt_commercial_name or '',
        'english_name':        sp.english_name or '',
        'alt_english_name':    sp.alt_english_name or '',
        'swedish_name':        sp.swedish_name or '',
        'alt_swedish_name':    sp.alt_swedish_name or '',
        'portuguese_name':     sp.portuguese_name or '',
        'alt_portuguese_name': sp.alt_portuguese_name or '',
        'origin':              sp.origin or '',
        'cites_listed':        sp.cites_listed or False,
        'aliases':             aliases,
        'images':              [_fmt_image(img) for img in p.images],
    })


@app.route('/api/products/<int:product_id>', methods=['PUT'])
def api_product_edit(product_id):
    """Save edits to a single product."""
    p = Product.query.get_or_404(product_id)
    data = request.get_json(force=True)

    errors = []

    # --- Price ---
    if 'price' in data:
        try:
            val = float(data['price'])
            if val < 0:
                raise ValueError
            p.price = round(val, 2)
        except (ValueError, TypeError):
            errors.append('Price must be a positive number.')

    # --- Stock ---
    if 'in_stock' in data:
        p.in_stock = bool(data['in_stock'])

    # --- Numeric dimensions ---
    for field in ('thickness_mm', 'width_mm', 'length_mm', 'weight_kg'):
        if field in data:
            raw = data[field]
            if raw == '' or raw is None:
                setattr(p, field, None)
            else:
                try:
                    setattr(p, field, float(raw))
                except (ValueError, TypeError):
                    errors.append(f'{field} must be a number.')

    # --- Free-text / lookup fields ---
    if 'product_url' in data:
        p.product_url = data['product_url'].strip() or None

    if 'format' in data:
        name = data['format'].strip()
        if name:
            fmt = Format.query.filter_by(name=name).first()
            if not fmt:
                fmt = Format(name=name)
                db.session.add(fmt)
                db.session.flush()
            p.format_id = fmt.format_id
        else:
            p.format_id = None

    if 'grade' in data:
        from models import Grade
        name = data['grade'].strip()
        if name:
            grade = Grade.query.filter_by(name=name).first()
            if not grade:
                grade = Grade(name=name)
                db.session.add(grade)
                db.session.flush()
            p.grade_id = grade.grade_id
        else:
            p.grade_id = None

    if errors:
        return jsonify({'ok': False, 'errors': errors}), 400

    p.last_updated = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True})


def _fmt_image(img):
    """Serialise a ProductImage to a dict for the API."""
    if img.source_type == 'upload':
        src = f'/static/product-images/{img.filename}'
    else:
        src = img.url or ''
    return {
        'image_id':    img.image_id,
        'source_type': img.source_type,
        'src':         src,
        'caption':     img.caption or '',
        'sort_order':  img.sort_order,
    }


@app.route('/api/products/<int:product_id>/images', methods=['POST'])
def api_image_upload(product_id):
    """Upload a file or save a URL as a product image."""
    p = Product.query.get_or_404(product_id)

    # --- URL image ---
    if request.is_json:
        data = request.get_json(force=True)
        url  = (data.get('url') or '').strip()
        if not url:
            return jsonify({'ok': False, 'error': 'No URL provided.'}), 400
        caption = (data.get('caption') or '').strip()
        max_order = db.session.query(db.func.max(ProductImage.sort_order))\
                              .filter_by(product_id=product_id).scalar() or 0
        img = ProductImage(product_id=product_id, source_type='url',
                           url=url, caption=caption, sort_order=max_order + 1)
        db.session.add(img)
        db.session.commit()
        return jsonify({'ok': True, 'image': _fmt_image(img)})

    # --- File upload ---
    if 'file' not in request.files:
        return jsonify({'ok': False, 'error': 'No file provided.'}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({'ok': False, 'error': 'Empty filename.'}), 400
    if not allowed_file(f.filename):
        return jsonify({'ok': False, 'error': 'File type not allowed. Use JPG, PNG, WebP or GIF.'}), 400

    ext      = f.filename.rsplit('.', 1)[1].lower()
    filename = f'{product_id}_{uuid.uuid4().hex}.{ext}'
    f.save(os.path.join(UPLOAD_FOLDER, filename))

    caption   = (request.form.get('caption') or '').strip()
    max_order = db.session.query(db.func.max(ProductImage.sort_order))\
                          .filter_by(product_id=product_id).scalar() or 0
    img = ProductImage(product_id=product_id, source_type='upload',
                       filename=filename, caption=caption, sort_order=max_order + 1)
    db.session.add(img)
    db.session.commit()
    return jsonify({'ok': True, 'image': _fmt_image(img)})


@app.route('/api/images/<int:image_id>', methods=['DELETE'])
def api_image_delete(image_id):
    """Delete a product image (file + DB record)."""
    img = ProductImage.query.get_or_404(image_id)
    if img.source_type == 'upload' and img.filename:
        path = os.path.join(UPLOAD_FOLDER, img.filename)
        if os.path.exists(path):
            os.remove(path)
    db.session.delete(img)
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/images/<int:image_id>/caption', methods=['PATCH'])
def api_image_caption(image_id):
    """Update the caption of an image."""
    img = ProductImage.query.get_or_404(image_id)
    data = request.get_json(force=True)
    img.caption = (data.get('caption') or '').strip()
    db.session.commit()
    return jsonify({'ok': True})


def _fmt_dims(p):
    parts = []
    if p.thickness_mm: parts.append(f'{p.thickness_mm:g}')
    if p.width_mm:     parts.append(f'{p.width_mm:g}')
    if p.length_mm:    parts.append(f'{p.length_mm:g}')
    return (' × '.join(parts) + ' mm') if parts else ''


if __name__ == '__main__':
    print("\n" + "="*50)
    print("Tonewood Price Comparison is starting...")
    print("Open your browser and go to: http://localhost:5000")
    print("Press CTRL+C to stop the server")
    print("="*50 + "\n")
    app.run(debug=True, port=5000)