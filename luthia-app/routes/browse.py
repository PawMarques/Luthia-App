"""Browse page and product catalogue API.

Provides:
  GET /browse               — product browsing page (populates filter dropdowns)
  GET /api/products         — paginated, filterable, sortable product list (JSON)
  GET /api/products/<id>    — full product detail including species names (JSON)
  PUT /api/products/<id>    — update editable product fields (JSON)
"""

import traceback
from datetime import datetime, timezone

from flask import Blueprint, jsonify, render_template, request
from sqlalchemy import func

from helpers import (
    CATEGORY_CLASSES,
    VENDOR_FLAGS,
    fmt_dims,
    fmt_image,
    staleness_info,
)
from models import Category, Format, Grade, Product, Species, Vendor, db

browse_bp = Blueprint('browse', __name__)

# Number of products shown per page in the catalogue table.
PER_PAGE = 50


# ---------------------------------------------------------------------------
# Page route
# ---------------------------------------------------------------------------

@browse_bp.route('/browse')
def browse():
    """Render the browse page with pre-populated filter dropdowns.

    Products themselves are loaded asynchronously via /api/products so the
    initial page load stays fast even with a large catalogue.
    """
    try:
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

        species_opts = '<option value="">All species</option>\n' + ''.join(
            f'<option value="{s.species_id}">'
            f'{s.commercial_name or s.scientific_name} ({cnt})</option>\n'
            for s, cnt in species_list
        )
        vendor_opts = '<option value="">All vendors</option>\n' + ''.join(
            f'<option value="{v.vendor_id}">'
            f'{v.name} · {v.country} {VENDOR_FLAGS.get(v.country, "")} ({cnt})</option>\n'
            for v, cnt in vendors
        )
        cat_opts = '<option value="">All categories</option>\n' + ''.join(
            f'<option value="{c.category_id}" data-name="{c.name}">'
            f'{c.name} ({cnt})</option>\n'
            for c, cnt in categories
        )

        return render_template(
            'index.html',
            species_opts=species_opts,
            vendor_opts=vendor_opts,
            cat_opts=cat_opts,
            total_products=Product.query.count(),
            vendor_count=len(vendors),
            active_nav='browse',
            breadcrumb=[('Browse Woods', None)],
            page_title='Luthia · Browse Woods',
        )

    except Exception as e:
        return f'<h1>Error</h1><p>{e}</p><pre>{traceback.format_exc()}</pre>'


# ---------------------------------------------------------------------------
# Products list API
# ---------------------------------------------------------------------------

@browse_bp.route('/api/products')
def api_products():
    """Return a paginated, filtered and sorted list of products as JSON.

    Also returns available Format options when a category is selected,
    enabling the dynamic format dropdown in the UI.
    """
    species_id  = request.args.get('species_id',  type=int)
    vendor_id   = request.args.get('vendor_id',   type=int)
    category_id = request.args.get('category_id', type=int)
    format_id   = request.args.get('format_id',   type=int)
    max_price   = request.args.get('max_price',   type=float)
    sort_by     = request.args.get('sort',  'price')
    sort_order  = request.args.get('order', 'asc')
    page        = request.args.get('page',  1, type=int)

    query = _build_product_query(species_id, vendor_id, category_id, format_id, max_price)
    query = _apply_sort(query, sort_by, sort_order)

    total    = query.count()
    products = query.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()

    # Dynamic format options — only relevant when a category filter is active.
    formats = _formats_for_category(category_id) if category_id else []

    return jsonify({
        'total':   total,
        'page':    page,
        'pages':   max(1, (total + PER_PAGE - 1) // PER_PAGE),
        'rows':    [_product_row(p) for p in products],
        'formats': formats,
    })


def _build_product_query(species_id, vendor_id, category_id, format_id, max_price):
    """Apply filter parameters to the Product query and return it."""
    q = Product.query
    if species_id:  q = q.filter_by(species_id=species_id)
    if vendor_id:   q = q.filter_by(vendor_id=vendor_id)
    if category_id: q = q.filter_by(category_id=category_id)
    if format_id:   q = q.filter_by(format_id=format_id)
    if max_price:   q = q.filter(Product.price <= max_price)
    return q


def _apply_sort(query, sort_by: str, sort_order: str):
    """Add an ORDER BY clause to a product query based on the requested column."""
    asc = sort_order == 'asc'

    if sort_by == 'species':
        return query.join(Species).order_by(
            Species.commercial_name.asc() if asc else Species.commercial_name.desc())
    if sort_by == 'vendor':
        return query.join(Vendor).order_by(
            Vendor.name.asc() if asc else Vendor.name.desc())
    if sort_by == 'category':
        return query.join(Category).order_by(
            Category.name.asc() if asc else Category.name.desc())
    if sort_by == 'grade':
        return query.outerjoin(Grade).order_by(
            Grade.name.asc() if asc else Grade.name.desc())
    if sort_by == 'format':
        return query.outerjoin(Format).order_by(
            Format.name.asc() if asc else Format.name.desc())

    # Default: sort by price.
    return query.order_by(Product.price.asc() if asc else Product.price.desc())


def _formats_for_category(category_id: int) -> list[dict]:
    """Return Format options available for the given category (for the dynamic dropdown)."""
    rows = (
        db.session.query(Format, func.count(Product.product_id).label('cnt'))
        .join(Product, Product.format_id == Format.format_id)
        .filter(Product.category_id == category_id)
        .group_by(Format.format_id)
        .order_by(Format.name)
        .all()
    )
    return [{'id': f.format_id, 'name': f.name, 'count': cnt} for f, cnt in rows]


def _product_row(p) -> dict:
    """Serialise a Product to a table-row dict for the browse API response."""
    display_name = p.species.commercial_name or p.species.scientific_name
    listed       = p.species_as_listed or ''

    # Only show the alias label when it differs from both canonical names to
    # avoid redundant "(listed as: Mahogany)" next to "Mahogany".
    alias = (
        listed
        if listed
        and listed.lower() != display_name.lower()
        and listed.lower() != (p.species.scientific_name or '').lower()
        else ''
    )

    cat                  = p.category.name
    stale_date, stale_color = staleness_info(p.last_updated)

    return {
        'product_id':  p.product_id,
        'species':     display_name,
        'alias':       alias,
        'vendor':      p.vendor.name,
        'vendor_flag': VENDOR_FLAGS.get(p.vendor.country, ''),
        'category':    cat,
        'cat_class':   CATEGORY_CLASSES.get(cat, 'cat-default'),
        'format':      p.format.name if p.format else '',
        'grade':       p.grade.name  if p.grade  else '',
        'price':       round(p.price, 2),
        'url':         p.product_url or '',
        'stale_date':  stale_date,
        'stale_color': stale_color,
    }


# ---------------------------------------------------------------------------
# Product detail API
# ---------------------------------------------------------------------------

@browse_bp.route('/api/products/<int:product_id>')
def api_product_detail(product_id):
    """Return the full detail payload for a single product."""
    p  = Product.query.get_or_404(product_id)
    sp = p.species
    cat = p.category.name

    stale_date, stale_color = staleness_info(p.last_updated)

    # Collect all known aliases, grouped by language, for the names panel.
    aliases: dict[str, list[str]] = {}
    for a in sp.aliases:
        lang = a.language or 'other'
        if a.alias_name not in aliases.setdefault(lang, []):
            aliases[lang].append(a.alias_name)

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
        'dimensions':          fmt_dims(p),
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
        'images':              [fmt_image(img) for img in p.images],
    })


# ---------------------------------------------------------------------------
# Product edit API
# ---------------------------------------------------------------------------

@browse_bp.route('/api/products/<int:product_id>', methods=['PUT'])
def api_product_edit(product_id):
    """Save inline edits to a product.  Returns {ok, errors} JSON."""
    p    = Product.query.get_or_404(product_id)
    data = request.get_json(force=True)
    errors = []

    if 'price' in data:
        try:
            val = float(data['price'])
            if val < 0:
                raise ValueError
            p.price = round(val, 2)
        except (ValueError, TypeError):
            errors.append('Price must be a positive number.')

    if 'in_stock' in data:
        p.in_stock = bool(data['in_stock'])

    # Numeric dimension fields — accept empty string or None to clear the value.
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

    if 'product_url' in data:
        p.product_url = data['product_url'].strip() or None

    if 'format' in data:
        p.format_id = _get_or_create_format(data['format'].strip())

    if 'grade' in data:
        p.grade_id = _get_or_create_grade(data['grade'].strip())

    if errors:
        return jsonify({'ok': False, 'errors': errors}), 400

    p.last_updated = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.commit()
    return jsonify({'ok': True})


def _get_or_create_format(name: str):
    """Return the format_id for *name*, creating a new Format row if needed."""
    if not name:
        return None
    fmt = Format.query.filter_by(name=name).first()
    if not fmt:
        fmt = Format(name=name)
        db.session.add(fmt)
        db.session.flush()
    return fmt.format_id


def _get_or_create_grade(name: str):
    """Return the grade_id for *name*, creating a new Grade row if needed."""
    if not name:
        return None
    grade = Grade.query.filter_by(name=name).first()
    if not grade:
        grade = Grade(name=name)
        db.session.add(grade)
        db.session.flush()
    return grade.grade_id
