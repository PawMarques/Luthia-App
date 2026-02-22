from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
from datetime import datetime, timedelta
from models import db, Species, SpeciesAlias, Product, Vendor, Category, Grade, Format, ProductImage, \
                   InstrumentTemplate, TemplateVariant, Build, BuildPart
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

# Category badge CSS classes
CATEGORY_CLASSES = {
    'Body Blank':         'cat-body',
    'Neck Blank':         'cat-neck',
    'Fretboard Blank':    'cat-fretboard',
    'Top Blank':          'cat-top',
    'Carpentry lumber':   'cat-carpentry',
    'Finished Fretboard': 'cat-finished',
}

VENDOR_FLAGS = {
    'Sweden':   '🇸🇪',
    'Portugal': '🇵🇹',
    'Italy':    '🇮🇹',
    'Spain':    '🇪🇸',
}

def category_badge(name):
    cls = CATEGORY_CLASSES.get(name, 'cat-default')
    return f'<span class="cat-badge {cls}">{name}</span>'

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
    return redirect(url_for('builds_index'))

@app.route('/browse')
def browse():
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

        return render_template('index.html',
            species_opts=species_opts,
            vendor_opts=vendor_opts,
            cat_opts=cat_opts,
            total_products=total_products,
            vendor_count=len(vendors),
            active_nav='browse',
            breadcrumb=[('Browse Woods', None)],
            page_title='Luthia · Browse Woods',
        )

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
            'cat_class':   CATEGORY_CLASSES.get(cat, 'cat-default'),
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
        'cat_class':           CATEGORY_CLASSES.get(cat, 'cat-default'),
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


""" BUILD PLANNER START """

# ---------------------------------------------------------------------------
# Helper: category name → category_id lookup
# ---------------------------------------------------------------------------
def _category_id(name):
    c = Category.query.filter_by(name=name).first()
    return c.category_id if c else None


# ---------------------------------------------------------------------------
# Helper: determine which part roles a variant needs
# ---------------------------------------------------------------------------
def _roles_for_variant(variant):
    """Return ordered list of part role names for a given TemplateVariant."""
    roles = ['body', 'neck', 'fretboard']
    if variant.has_top:
        roles.append('top')
    return roles


# ---------------------------------------------------------------------------
# Helper: find candidate products for a given role + variant
# ---------------------------------------------------------------------------
ROLE_CATEGORIES = {
    'body':      'Body Blank',
    'neck':      'Neck Blank',
    'fretboard': 'Fretboard Blank',
    'top':       'Top Blank',
}

THICKNESS_WARN_LIMIT = 45.0   # mm — flag if body + top exceeds this


def _candidate_products(role, variant):
    """
    Return list of candidate Product rows for a build part slot.

    Tier 1 — category match (always applied).
    Tier 2 — dimension filter (applied only when product has dimension data).
              Products without dimensions are included but flagged dims_unverified.

    For neck-through builds the neck blank length filter uses neck_length_thru_mm.
    """
    cat_name = ROLE_CATEGORIES.get(role)
    if not cat_name:
        return []

    cat_id = _category_id(cat_name)
    if not cat_id:
        return []

    query = Product.query.filter_by(category_id=cat_id)

    # Determine required minimum blank dimensions from variant
    min_length = min_width = min_thickness = None

    if role == 'body':
        min_length    = variant.body_length_mm
        min_width     = variant.body_width_mm
        min_thickness = variant.body_thickness_mm

    elif role == 'neck':
        if variant.construction == 'neck-through':
            min_length = variant.neck_length_thru_mm
        else:
            min_length = variant.neck_length_mm
        min_width     = variant.nut_width_mm        # narrowest point — safe lower bound
        min_thickness = variant.neck_thickness_12f_mm

    elif role == 'fretboard':
        # Fretboard length: fret 24 sits at scale × 0.75 from the nut; add 20mm overhang
        min_length    = (variant.scale_mm or 864) * 0.75 + 20
        min_width     = (variant.nut_width_mm or 38) + 10
        min_thickness = 6.0   # standard fretboard blank minimum

    elif role == 'top':
        min_length    = variant.body_length_mm
        min_width     = variant.body_width_mm
        min_thickness = 4.0   # typical top blank

    products = query.order_by(Product.price.asc()).all()

    results = []
    for p in products:
        has_dims = any([p.length_mm, p.width_mm, p.thickness_mm])
        dim_ok   = True   # assume ok if no dims

        if has_dims:
            if min_length    and p.length_mm    and p.length_mm    < min_length:    dim_ok = False
            if min_width     and p.width_mm     and p.width_mm     < min_width:     dim_ok = False
            if min_thickness and p.thickness_mm and p.thickness_mm < min_thickness: dim_ok = False

        if dim_ok:
            results.append({
                'product':        p,
                'dims_unverified': not has_dims,
            })

    return results


def _check_thickness_warning(build):
    """
    Set thickness_warning on the 'body' and 'top' BuildPart rows if their
    combined thickness exceeds THICKNESS_WARN_LIMIT.
    Clears the flag if no top is selected.
    """
    body_part = next((p for p in build.parts if p.role == 'body'), None)
    top_part  = next((p for p in build.parts if p.role == 'top'),  None)

    if not body_part or not top_part:
        # Nothing to warn about
        if body_part: body_part.thickness_warning = False
        if top_part:  top_part.thickness_warning  = False
        return

    body_t = (body_part.product.thickness_mm
              if body_part.product_id and body_part.product else None)
    top_t  = (top_part.product.thickness_mm
              if top_part.product_id  and top_part.product  else None)

    warn = False
    if body_t and top_t:
        warn = (body_t + top_t) > THICKNESS_WARN_LIMIT

    body_part.thickness_warning = warn
    top_part.thickness_warning  = warn


# ---------------------------------------------------------------------------
# /templates  — browse instrument templates and their reference dimensions
# ---------------------------------------------------------------------------
@app.route('/templates')
def templates_index():
    templates = InstrumentTemplate.query.order_by(InstrumentTemplate.name).all()

    cards_html = ''
    for t in templates:
        type_label = t.instrument_type.capitalize() if t.instrument_type else 'Instrument'

        variants_html = ''
        for v in sorted(t.variants, key=lambda x: (x.strings, x.scale_mm)):
            construction_label = v.construction.replace('-', ' ').title() if v.construction else '—'
            has_top_badge = ' <span class="badge-grade">+ Top</span>' if v.has_top else ''

            dim_rows = ''
            if v.body_length_mm:
                dim_rows += f'<div class="tpl-dim-row"><span>Body blank</span><span>{v.body_length_mm:.0f} × {v.body_width_mm:.0f} × {v.body_thickness_mm:.0f} mm</span></div>'
            if v.neck_length_mm or v.neck_length_thru_mm:
                neck_len = v.neck_length_thru_mm if v.construction == 'neck-through' else v.neck_length_mm
                neck_label = 'Neck blank (thru)' if v.construction == 'neck-through' else 'Neck blank'
                dim_rows += f'<div class="tpl-dim-row"><span>{neck_label}</span><span>{neck_len:.0f} mm</span></div>'
            if v.nut_width_mm:
                dim_rows += f'<div class="tpl-dim-row"><span>Nut width</span><span>{v.nut_width_mm:.1f} mm</span></div>'
            if v.overall_length_mm:
                dim_rows += f'<div class="tpl-dim-row"><span>Overall length</span><span>{v.overall_length_mm:.0f} mm</span></div>'

            variants_html += f"""
<div class="tpl-variant">
  <div class="tpl-variant-header">
    <div>
      <span class="tpl-variant-label">{v.label}</span>{has_top_badge}
      <span class="tpl-construction-badge">{construction_label}</span>
    </div>
  </div>
  <div class="tpl-dims">
    <div class="tpl-dim-row tpl-dim-scale">
      <span>Scale</span><span>{v.scale_mm:.1f} mm ({v.strings}-string)</span>
    </div>
    {dim_rows}
  </div>
</div>"""

        total_builds = len(t.builds)
        builds_note = f'<span class="tpl-builds-count">{total_builds} build{"s" if total_builds != 1 else ""}</span>' if total_builds else ''

        cards_html += f"""
<div class="tpl-card">
  <div class="tpl-card-header">
    <div>
      <div class="tpl-card-title">{t.name}</div>
      <div class="tpl-card-type">{type_label} · {len(t.variants)} variant{"s" if len(t.variants) != 1 else ""}</div>
    </div>
    <div style="display:flex;align-items:center;gap:10px;">
      {builds_note}
      <a href="/templates/{t.template_id}/edit" class="btn-sm">Edit</a>
      <a href="/builds/new" class="btn-sm btn-sm--accent">New Build</a>
    </div>
  </div>
  {variants_html}
</div>"""

    if not cards_html:
        cards_html = '<p style="color:#52525b;text-align:center;padding:40px 0;">No templates found.</p>'

    return render_template('templates/index.html',
        cards_html=cards_html,
        active_nav='templates',
        breadcrumb=[('Templates', None)],
        page_title='Luthia · Templates',
    )


# ---------------------------------------------------------------------------
# /templates/<id>/edit  — edit template name/type and all variant dimensions
# ---------------------------------------------------------------------------
@app.route('/templates/<int:template_id>/edit', methods=['GET', 'POST'])
def templates_edit(template_id):
    t = InstrumentTemplate.query.get_or_404(template_id)

    errors = []

    if request.method == 'POST':
        # --- Template-level fields ---
        name = request.form.get('name', '').strip()
        instrument_type = request.form.get('instrument_type', '').strip().lower()
        notes = request.form.get('notes', '').strip()

        if not name:
            errors.append('Template name is required.')
        elif name != t.name and InstrumentTemplate.query.filter_by(name=name).first():
            errors.append('A template with that name already exists.')

        if not errors:
            t.name = name
            t.instrument_type = instrument_type or None
            t.notes = notes or None

            # --- Variant fields ---
            def _f(key):
                raw = request.form.get(key, '').strip()
                try:
                    return float(raw) if raw else None
                except ValueError:
                    return None

            for v in t.variants:
                p = f'v{v.variant_id}_'
                v.label         = request.form.get(f'{p}label', v.label).strip() or v.label
                v.strings       = int(request.form.get(f'{p}strings', v.strings) or v.strings)
                v.scale_mm      = float(request.form.get(f'{p}scale_mm', '') or v.scale_mm)
                v.construction  = request.form.get(f'{p}construction', v.construction)
                v.has_top       = request.form.get(f'{p}has_top') == '1'

                v.body_length_mm      = _f(f'{p}body_length_mm')
                v.body_width_mm       = _f(f'{p}body_width_mm')
                v.body_thickness_mm   = _f(f'{p}body_thickness_mm')
                v.neck_length_mm      = _f(f'{p}neck_length_mm')
                v.neck_length_thru_mm = _f(f'{p}neck_length_thru_mm')
                v.nut_width_mm        = _f(f'{p}nut_width_mm')
                v.neck_width_heel_mm  = _f(f'{p}neck_width_heel_mm')
                v.neck_thickness_1f_mm  = _f(f'{p}neck_thickness_1f_mm')
                v.neck_thickness_12f_mm = _f(f'{p}neck_thickness_12f_mm')
                v.headstock_length_mm = _f(f'{p}headstock_length_mm')
                v.headstock_width_mm  = _f(f'{p}headstock_width_mm')
                v.overall_length_mm   = _f(f'{p}overall_length_mm')

            db.session.commit()
            return f'<script>window.location="/templates"</script>'

    def fv(val):
        """Format a float for input value — blank if None."""
        return '' if val is None else f'{val:g}'

    variants_html = ''
    for v in sorted(t.variants, key=lambda x: (x.strings, x.scale_mm)):
        p = f'v{v.variant_id}_'
        bolt_sel  = 'selected' if v.construction == 'bolt-on'      else ''
        thru_sel  = 'selected' if v.construction == 'neck-through'  else ''
        top_chk   = 'checked'  if v.has_top else ''

        variants_html += f"""
<div class="tpl-edit-variant">
  <div class="tpl-edit-variant-title">Variant — {v.label}</div>

  <div class="tpl-edit-grid">
    <div class="form-group">
      <label class="filter-label">Label</label>
      <input type="text" name="{p}label" class="filter-input" value="{v.label}" required>
    </div>
    <div class="form-group">
      <label class="filter-label">Strings</label>
      <input type="number" name="{p}strings" class="filter-input" value="{v.strings}" min="1" max="12" required>
    </div>
    <div class="form-group">
      <label class="filter-label">Scale (mm)</label>
      <input type="number" name="{p}scale_mm" class="filter-input" value="{fv(v.scale_mm)}" step="0.1" required>
    </div>
    <div class="form-group">
      <label class="filter-label">Construction</label>
      <select name="{p}construction" class="filter-select">
        <option value="bolt-on" {bolt_sel}>Bolt-on</option>
        <option value="neck-through" {thru_sel}>Neck-through</option>
      </select>
    </div>
  </div>

  <div class="tpl-edit-section-label">Body Blank</div>
  <div class="tpl-edit-grid">
    <div class="form-group">
      <label class="filter-label">Length (mm)</label>
      <input type="number" name="{p}body_length_mm" class="filter-input" value="{fv(v.body_length_mm)}" step="0.1">
    </div>
    <div class="form-group">
      <label class="filter-label">Width (mm)</label>
      <input type="number" name="{p}body_width_mm" class="filter-input" value="{fv(v.body_width_mm)}" step="0.1">
    </div>
    <div class="form-group">
      <label class="filter-label">Thickness (mm)</label>
      <input type="number" name="{p}body_thickness_mm" class="filter-input" value="{fv(v.body_thickness_mm)}" step="0.1">
    </div>
    <div class="form-group">
      <label class="filter-label" style="display:flex;align-items:center;gap:8px;">
        <input type="checkbox" name="{p}has_top" value="1" {top_chk}
               class="accent-checkbox" style="width:14px;height:14px;">
        Includes top blank
      </label>
    </div>
  </div>

  <div class="tpl-edit-section-label">Neck Blank</div>
  <div class="tpl-edit-grid">
    <div class="form-group">
      <label class="filter-label">Length bolt-on (mm)</label>
      <input type="number" name="{p}neck_length_mm" class="filter-input" value="{fv(v.neck_length_mm)}" step="0.1">
    </div>
    <div class="form-group">
      <label class="filter-label">Length neck-thru (mm)</label>
      <input type="number" name="{p}neck_length_thru_mm" class="filter-input" value="{fv(v.neck_length_thru_mm)}" step="0.1">
    </div>
    <div class="form-group">
      <label class="filter-label">Nut width (mm)</label>
      <input type="number" name="{p}nut_width_mm" class="filter-input" value="{fv(v.nut_width_mm)}" step="0.1">
    </div>
    <div class="form-group">
      <label class="filter-label">Width at heel (mm)</label>
      <input type="number" name="{p}neck_width_heel_mm" class="filter-input" value="{fv(v.neck_width_heel_mm)}" step="0.1">
    </div>
    <div class="form-group">
      <label class="filter-label">Thickness at 1st fret (mm)</label>
      <input type="number" name="{p}neck_thickness_1f_mm" class="filter-input" value="{fv(v.neck_thickness_1f_mm)}" step="0.1">
    </div>
    <div class="form-group">
      <label class="filter-label">Thickness at 12th fret (mm)</label>
      <input type="number" name="{p}neck_thickness_12f_mm" class="filter-input" value="{fv(v.neck_thickness_12f_mm)}" step="0.1">
    </div>
  </div>

  <div class="tpl-edit-section-label">Headstock &amp; Overall</div>
  <div class="tpl-edit-grid">
    <div class="form-group">
      <label class="filter-label">Headstock length (mm)</label>
      <input type="number" name="{p}headstock_length_mm" class="filter-input" value="{fv(v.headstock_length_mm)}" step="0.1">
    </div>
    <div class="form-group">
      <label class="filter-label">Headstock width (mm)</label>
      <input type="number" name="{p}headstock_width_mm" class="filter-input" value="{fv(v.headstock_width_mm)}" step="0.1">
    </div>
    <div class="form-group">
      <label class="filter-label">Overall length (mm)</label>
      <input type="number" name="{p}overall_length_mm" class="filter-input" value="{fv(v.overall_length_mm)}" step="0.1">
    </div>
  </div>
</div>"""

    error_html = ''
    if errors:
        error_html = '<div class="tpl-edit-error">' + '<br>'.join(errors) + '</div>'

    return render_template('templates/edit.html',
        t=t,
        variants_html=variants_html,
        error_html=error_html,
        active_nav='templates',
        breadcrumb=[('Templates', '/templates'), (f'Edit {t.name}', None)],
        page_title=f'Luthia · Templates · Edit {t.name}',
    )


# ---------------------------------------------------------------------------
# /builds  — list all saved builds
# ---------------------------------------------------------------------------
@app.route('/builds')
def builds_index():
    builds = Build.query.order_by(Build.updated_at.desc()).all()

    cards_html = ''
    if builds:
        for b in builds:
            parts_done  = sum(1 for p in b.parts if p.product_id)
            parts_total = len(b.parts)
            progress_pct = int(parts_done / parts_total * 100) if parts_total else 0
            price_str = f'{b.total_price:,.0f} SEK' if b.total_price else '—'
            updated   = b.updated_at.strftime('%Y-%m-%d') if b.updated_at else ''
            warn = any(p.thickness_warning for p in b.parts)
            warn_html = ' <span title="Thickness warning" style="color:#f59e0b;">⚠</span>' if warn else ''

            cards_html += f"""
<a href="/builds/{b.build_id}" class="build-card">
  <div class="build-card-title">{b.name}{warn_html}</div>
  <div class="build-card-sub">{b.template.name} · {b.variant.label}</div>
  <div class="build-progress-bar"><div class="build-progress-fill" style="width:{progress_pct}%"></div></div>
  <div class="build-card-meta">
    <span>{parts_done}/{parts_total} parts</span>
    <span class="build-card-price">{price_str}</span>
    <span style="color:#3f3f46;">{updated}</span>
  </div>
</a>"""
    else:
        cards_html = '<p style="color:#52525b;text-align:center;padding:40px 0;">No builds yet. <a href="/builds/new" class="accent-link">Create your first one!</a></p>'

    return render_template('builds/index.html',
        cards_html=cards_html,
        active_nav='builds',
        breadcrumb=[('Build Planner', None)],
        page_title='Luthia · Build Planner',
    )


# ---------------------------------------------------------------------------
# /builds/new  — pick template + variant, name the build
# ---------------------------------------------------------------------------
@app.route('/builds/new', methods=['GET', 'POST'])
def builds_new():
    if request.method == 'POST':
        template_id = request.form.get('template_id', type=int)
        variant_id  = request.form.get('variant_id',  type=int)
        name        = request.form.get('name', '').strip()

        if not template_id or not variant_id or not name:
            error = 'Please fill in all fields.'
        else:
            variant = TemplateVariant.query.get(variant_id)
            if not variant or variant.template_id != template_id:
                error = 'Invalid selection.'
            else:
                build = Build(name=name, template_id=template_id, variant_id=variant_id)
                db.session.add(build)
                db.session.flush()

                # Create empty part slots
                for role in _roles_for_variant(variant):
                    db.session.add(BuildPart(build_id=build.build_id, role=role))

                db.session.commit()
                return f'<script>window.location="/builds/{build.build_id}"</script>'

    templates = InstrumentTemplate.query.order_by(InstrumentTemplate.name).all()

    # Build template→variants data for dynamic variant dropdown
    tpl_data = {}
    for t in templates:
        tpl_data[t.template_id] = [
            {'id': v.variant_id, 'label': v.label, 'construction': v.construction,
             'has_top': v.has_top}
            for v in t.variants
        ]

    tpl_opts = '<option value="">Select instrument…</option>'
    for t in templates:
        tpl_opts += f'<option value="{t.template_id}">{t.name}</option>'

    return render_template('builds/new.html',
        tpl_opts=tpl_opts,
        tpl_data=tpl_data,
        active_nav='builds',
        breadcrumb=[('Build Planner', '/builds'), ('New Build', None)],
        page_title='Luthia · New Build',
    )


# ---------------------------------------------------------------------------
# /builds/<id>  — view / edit a saved build
# ---------------------------------------------------------------------------
@app.route('/builds/<int:build_id>')
def builds_detail(build_id):
    build = Build.query.get_or_404(build_id)
    variant = build.variant

    parts_html = ''
    total = 0.0

    role_icons = {'body': '🪵', 'neck': '🎸', 'fretboard': '📏', 'top': '✨'}

    for part in build.parts:
        role_label = part.role.capitalize()
        icon = role_icons.get(part.role, '•')

        if part.product_id and part.product:
            p = part.product
            species = p.species.commercial_name or p.species.scientific_name
            vendor  = p.vendor.name
            flag    = VENDOR_FLAGS.get(p.vendor.country, '')
            price   = p.price
            total  += price

            dims_parts = []
            if p.thickness_mm: dims_parts.append(f'{p.thickness_mm:.0f}mm thick')
            if p.width_mm:     dims_parts.append(f'{p.width_mm:.0f}mm wide')
            if p.length_mm:    dims_parts.append(f'{p.length_mm:.0f}mm long')
            dims_str = ' · '.join(dims_parts) if dims_parts else 'dimensions not specified'

            warn_html = ''
            if part.thickness_warning:
                warn_html = '<div class="part-warning">⚠ Combined body + top thickness exceeds 45mm — body may need planing</div>'
            if part.dims_unverified:
                warn_html += '<div class="part-notice">ℹ Dimensions not specified by vendor — verify suitability before ordering</div>'

            link_html = f'<a href="{p.product_url}" target="_blank" class="view-link" style="font-size:11px;">View ↗</a>' if p.product_url else ''

            grade_html = f'<span class="badge-grade">{p.grade.name}</span>' if p.grade else ''

            parts_html += f"""
<div class="part-row">
  <div class="part-role">{icon} {role_label}</div>
  <div class="part-detail">
    <div class="part-species">{species} {grade_html}</div>
    <div class="part-meta">{vendor} {flag} · {dims_str}</div>
    {warn_html}
  </div>
  <div class="part-price">{price:,.0f} <span style="color:#52525b;font-size:11px;">SEK</span></div>
  <div class="part-actions">
    {link_html}
    <button class="btn-sm" onclick="openPicker('{part.role}', {part.part_id})">Change</button>
  </div>
</div>"""
        else:
            parts_html += f"""
<div class="part-row part-empty">
  <div class="part-role">{icon} {role_label}</div>
  <div class="part-detail" style="color:#52525b;">No product selected</div>
  <div class="part-price">—</div>
  <div class="part-actions">
    <button class="btn-select" onclick="openPicker('{part.role}', {part.part_id})">Select</button>
  </div>
</div>"""

    # Dimension reference panel
    ref = variant
    construction_label = ref.construction.replace('-', ' ').title()
    neck_len = ref.neck_length_thru_mm if ref.construction == 'neck-through' else ref.neck_length_mm
    neck_label = f"Neck-thru blank: {neck_len:.0f}mm" if ref.construction == 'neck-through' else f"Neck blank (nut→heel): {neck_len:.0f}mm"

    case_warn = ''
    if ref.overall_length_mm and ref.overall_length_mm > 1250:
        case_warn = ' <span style="color:#f59e0b;" title="Exceeds standard case length of 1250mm">⚠</span>'
    if ref.body_width_mm and ref.body_width_mm > 380:
        case_warn += ' <span style="color:#f59e0b;" title="Exceeds standard case width of 380mm">⚠</span>'

    return render_template('builds/detail.html',
        build=build,
        variant=variant,
        parts_html=parts_html,
        total_str=f'{total:,.0f}',
        ref=ref,
        construction_label=construction_label,
        neck_label=neck_label,
        case_warn=case_warn,
        active_nav='builds',
        breadcrumb=[('Build Planner', '/builds'), (build.name, None)],
        page_title=f'Luthia · Build · {build.name}',
    )


# ---------------------------------------------------------------------------
# API: candidate products for a role
# ---------------------------------------------------------------------------
@app.route('/api/builds/<int:build_id>/candidates/<role>')
def api_build_candidates(build_id, role):
    build = Build.query.get_or_404(build_id)
    candidates = _candidate_products(role, build.variant)

    rows = []
    for c in candidates:
        p = c['product']
        dims_parts = []
        if p.thickness_mm: dims_parts.append(f'{p.thickness_mm:.0f}mm thick')
        if p.width_mm:     dims_parts.append(f'{p.width_mm:.0f}mm wide')
        if p.length_mm:    dims_parts.append(f'{p.length_mm:.0f}mm long')

        rows.append({
            'id':              p.product_id,
            'species':         p.species.commercial_name or p.species.scientific_name,
            'vendor':          p.vendor.name,
            'flag':            VENDOR_FLAGS.get(p.vendor.country, ''),
            'grade':           p.grade.name if p.grade else '',
            'price':           round(p.price, 2),
            'dims':            ' · '.join(dims_parts),
            'dims_unverified': c['dims_unverified'],
            'url':             p.product_url or '',
        })

    return jsonify(rows)


# ---------------------------------------------------------------------------
# API: update a build part (assign product)
# ---------------------------------------------------------------------------
@app.route('/api/builds/<int:build_id>/parts/<int:part_id>', methods=['PATCH'])
def api_build_part_update(build_id, part_id):
    build = Build.query.get_or_404(build_id)
    part  = BuildPart.query.filter_by(part_id=part_id, build_id=build_id).first_or_404()

    data = request.get_json()
    product_id = data.get('product_id')

    part.product_id = product_id

    # Set dims_unverified flag
    if product_id:
        p = Product.query.get(product_id)
        part.dims_unverified = not any([p.length_mm, p.width_mm, p.thickness_mm])
    else:
        part.dims_unverified = False

    # Recompute thickness warning across body + top
    _check_thickness_warning(build)

    # Recompute total price
    build.compute_total()
    build.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'ok': True, 'total': build.total_price})


# ---------------------------------------------------------------------------
# API: delete a build
# ---------------------------------------------------------------------------
@app.route('/api/builds/<int:build_id>', methods=['DELETE'])
def api_build_delete(build_id):
    build = Build.query.get_or_404(build_id)
    db.session.delete(build)
    db.session.commit()
    return jsonify({'ok': True})

""" BUILD PLANNER END """


if __name__ == '__main__':
    print("\n" + "="*50)
    print("Tonewood Price Comparison is starting...")
    print("Open your browser and go to: http://localhost:5000")
    print("Press CTRL+C to stop the server")
    print("="*50 + "\n")
    app.run(debug=True, port=5000)