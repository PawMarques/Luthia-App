"""Species guide routes and API.

Provides:
  GET /species                 — species reference guide page
  GET /api/species             — searchable, filterable species list (JSON)
  GET /api/species/<id>        — full species detail with product availability (JSON)
"""

from flask import Blueprint, jsonify, render_template, request
from sqlalchemy import func, or_

from helpers import VENDOR_FLAGS, paginate
from models import Category, Product, Species, SpeciesAlias, Vendor, db

species_bp = Blueprint('species', __name__)


# ---------------------------------------------------------------------------
# Page route
# ---------------------------------------------------------------------------

@species_bp.route('/species')
def species_index():
    """Render the species guide page."""
    total_species  = Species.query.count()
    cites_count    = Species.query.filter_by(cites_listed=True).count()
    in_stock_count = (
        db.session.query(func.count(func.distinct(Product.species_id)))
        .filter(Product.in_stock == True)
        .scalar() or 0
    )

    return render_template(
        'species.html',
        total_species=total_species,
        cites_count=cites_count,
        in_stock_count=in_stock_count,
        active_nav='species',
        breadcrumb=[('Species Guide', None)],
        page_title='Luthia · Species Guide',
    )


# ---------------------------------------------------------------------------
# API — list
# ---------------------------------------------------------------------------

@species_bp.route('/api/species')
def api_species_list():
    """Return a filtered, searchable list of species as JSON.

    Query params:
      q         — search string (matches all name fields and aliases)
      cites     — '1' to restrict to CITES-listed species
      available — '1' to restrict to species with at least one in-stock product
      page      — page number (default 1)
    """
    q_str     = (request.args.get('q') or '').strip()
    cites_only = request.args.get('cites')     == '1'
    avail_only = request.args.get('available') == '1'
    page       = request.args.get('page', 1, type=int)

    # Base query
    query = Species.query

    # Full-text search across all name columns + aliases
    if q_str:
        like = f'%{q_str}%'
        # Species IDs that match any alias
        alias_matches = (
            db.session.query(SpeciesAlias.species_id)
            .filter(SpeciesAlias.alias_name.ilike(like))
            .subquery()
        )
        query = query.filter(
            or_(
                Species.scientific_name.ilike(like),
                Species.commercial_name.ilike(like),
                Species.alt_commercial_name.ilike(like),
                Species.english_name.ilike(like),
                Species.alt_english_name.ilike(like),
                Species.swedish_name.ilike(like),
                Species.alt_swedish_name.ilike(like),
                Species.portuguese_name.ilike(like),
                Species.alt_portuguese_name.ilike(like),
                Species.origin.ilike(like),
                Species.species_id.in_(alias_matches),
            )
        )

    if cites_only:
        query = query.filter(Species.cites_listed == True)

    if avail_only:
        # Only species that have at least one in-stock product
        in_stock_ids = (
            db.session.query(Product.species_id)
            .filter(Product.in_stock == True)
            .distinct()
            .subquery()
        )
        query = query.filter(Species.species_id.in_(in_stock_ids))

    # Sort: species with products first, then alphabetically by commercial name
    query = query.order_by(
        Species.commercial_name.asc().nulls_last(),
        Species.scientific_name.asc(),
    )

    result = paginate(query, page, per_page=48)

    # Preload product availability stats in one query
    stats = _product_stats_for_species([s.species_id for s in result['items']])

    return jsonify({
        'total':    result['total'],
        'page':     result['page'],
        'pages':    result['pages'],
        'per_page': result['per_page'],
        'rows':     [_species_card(s, stats.get(s.species_id, {})) for s in result['items']],
    })


# ---------------------------------------------------------------------------
# API — detail
# ---------------------------------------------------------------------------

@species_bp.route('/api/species/<int:species_id>')
def api_species_detail(species_id):
    """Return the full detail payload for a single species."""
    sp = Species.query.get_or_404(species_id)

    # Collect aliases grouped by language
    aliases: dict[str, list[str]] = {}
    for a in sp.aliases:
        lang = a.language or 'other'
        if a.alias_name not in aliases.setdefault(lang, []):
            aliases[lang].append(a.alias_name)

    # Products — grouped by category, then vendor
    products_by_cat: dict[str, list[dict]] = {}
    for p in sorted(sp.products, key=lambda p: (p.category.name, p.vendor.name, p.price)):
        cat = p.category.name
        products_by_cat.setdefault(cat, []).append({
            'product_id':  p.product_id,
            'vendor':      p.vendor.name,
            'vendor_flag': VENDOR_FLAGS.get(p.vendor.country, ''),
            'format':      p.format.name if p.format else '',
            'grade':       p.grade.name  if p.grade  else '',
            'price':       round(p.price, 2),
            'currency':    p.currency or 'SEK',
            'in_stock':    p.in_stock,
        })

    stats = _product_stats_for_species([species_id])
    s = stats.get(species_id, {})

    return jsonify({
        'species_id':          sp.species_id,
        'scientific_name':     sp.scientific_name,
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
        'products_by_cat':     products_by_cat,
        'total_products':      s.get('total', 0),
        'in_stock_count':      s.get('in_stock', 0),
        'vendor_names':        s.get('vendors', []),
        'categories':          s.get('categories', []),
        'min_price':           s.get('min_price'),
        'max_price':           s.get('max_price'),
    })


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _product_stats_for_species(species_ids: list[int]) -> dict[int, dict]:
    """Fetch product availability stats for a list of species IDs in one query.

    Returns a dict mapping species_id → {total, in_stock, vendors, categories,
    min_price, max_price}.
    """
    if not species_ids:
        return {}

    rows = (
        db.session.query(
            Product.species_id,
            func.count(Product.product_id).label('total'),
            func.sum(func.cast(Product.in_stock, db.Integer)).label('in_stock'),
            func.min(Product.price).label('min_price'),
            func.max(Product.price).label('max_price'),
        )
        .filter(Product.species_id.in_(species_ids))
        .group_by(Product.species_id)
        .all()
    )

    result: dict[int, dict] = {
        r.species_id: {
            'total':     r.total,
            'in_stock':  r.in_stock or 0,
            'min_price': round(r.min_price, 2) if r.min_price else None,
            'max_price': round(r.max_price, 2) if r.max_price else None,
            'vendors':   [],
            'categories': [],
        }
        for r in rows
    }

    # Vendor names per species
    vendor_rows = (
        db.session.query(
            Product.species_id,
            Vendor.name,
            Vendor.country,
        )
        .join(Vendor, Vendor.vendor_id == Product.vendor_id)
        .filter(Product.species_id.in_(species_ids))
        .distinct()
        .order_by(Vendor.name)
        .all()
    )
    for sid, vname, vcountry in vendor_rows:
        if sid in result:
            flag = VENDOR_FLAGS.get(vcountry, '')
            result[sid]['vendors'].append({'name': vname, 'flag': flag})

    # Categories per species
    cat_rows = (
        db.session.query(Product.species_id, Category.name)
        .join(Category, Category.category_id == Product.category_id)
        .filter(Product.species_id.in_(species_ids))
        .distinct()
        .order_by(Category.name)
        .all()
    )
    for sid, cname in cat_rows:
        if sid in result:
            result[sid]['categories'].append(cname)

    return result


def _species_card(sp: Species, stats: dict) -> dict:
    """Serialise a Species to a card dict for the list API response."""
    return {
        'species_id':      sp.species_id,
        'scientific_name': sp.scientific_name,
        'commercial_name': sp.commercial_name or '',
        'swedish_name':    sp.swedish_name or '',
        'portuguese_name': sp.portuguese_name or '',
        'origin':          sp.origin or '',
        'cites_listed':    sp.cites_listed or False,
        'total_products':  stats.get('total', 0),
        'in_stock_count':  stats.get('in_stock', 0),
        'vendors':         stats.get('vendors', []),
        'categories':      stats.get('categories', []),
        'min_price':       stats.get('min_price'),
        'max_price':       stats.get('max_price'),
    }