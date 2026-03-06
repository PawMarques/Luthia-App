"""Vendor management routes and API.

Provides:
  GET    /vendors                  — vendor list page
  GET    /api/v1/vendors           — all vendors as JSON
  POST   /api/v1/vendors           — create a new vendor
  PATCH  /api/v1/vendors/<id>      — update vendor fields
  DELETE /api/v1/vendors/<id>      — deactivate (soft-delete) a vendor
"""

from flask import Blueprint, jsonify, render_template, request
from sqlalchemy import func

from helpers import VENDOR_FLAGS
from models import Product, Vendor, db

vendors_bp = Blueprint('vendors', __name__)


# ---------------------------------------------------------------------------
# Page route
# ---------------------------------------------------------------------------

@vendors_bp.route('/vendors')
def vendors_index():
    """Render the vendor management page."""
    vendors = (
        db.session.query(Vendor, func.count(Product.product_id).label('product_count'))
        .outerjoin(Product, Product.vendor_id == Vendor.vendor_id)
        .group_by(Vendor.vendor_id)
        .order_by(Vendor.name)
        .all()
    )

    return render_template(
        'vendors.html',
        vendors=vendors,
        active_nav='vendors',
        breadcrumb=[('Vendors', None)],
        page_title='Luthia · Vendors',
    )


# ---------------------------------------------------------------------------
# API — list
# ---------------------------------------------------------------------------

@vendors_bp.route('/api/v1/vendors', endpoint='api_vendors')
def api_vendors():
    """Return all vendors with product counts as JSON."""
    rows = (
        db.session.query(Vendor, func.count(Product.product_id).label('cnt'))
        .outerjoin(Product, Product.vendor_id == Vendor.vendor_id)
        .group_by(Vendor.vendor_id)
        .order_by(Vendor.name)
        .all()
    )
    return jsonify([_vendor_dict(v, cnt) for v, cnt in rows])


# ---------------------------------------------------------------------------
# API — create
# ---------------------------------------------------------------------------

@vendors_bp.route('/api/v1/vendors', methods=['POST'], endpoint='api_vendor_create')
def api_vendor_create():
    """Create a new vendor record.

    Expects JSON: {name, country?, currency?, website?}
    """
    data = request.get_json(force=True) or {}
    errors = _validate_vendor_data(data, is_new=True)
    if errors:
        return jsonify({'ok': False, 'errors': errors}), 400

    vendor = Vendor(
        name=data['name'].strip(),
        country=(data.get('country') or '').strip() or None,
        currency=(data.get('currency') or 'EUR').strip().upper(),
        website=(data.get('website') or '').strip() or None,
        active=True,
    )
    db.session.add(vendor)
    db.session.commit()
    return jsonify({'ok': True, 'vendor': _vendor_dict(vendor, 0)}), 201


# ---------------------------------------------------------------------------
# API — update
# ---------------------------------------------------------------------------

@vendors_bp.route('/api/v1/vendors/<int:vendor_id>', methods=['PATCH'], endpoint='api_vendor_update')
def api_vendor_update(vendor_id):
    """Update editable vendor fields.

    Accepts partial JSON — only fields present in the payload are changed.
    """
    vendor = Vendor.query.get_or_404(vendor_id)
    data   = request.get_json(force=True) or {}
    errors = _validate_vendor_data(data, is_new=False, current_vendor=vendor)
    if errors:
        return jsonify({'ok': False, 'errors': errors}), 400

    if 'name' in data:
        vendor.name = data['name'].strip()
    if 'country' in data:
        vendor.country = (data['country'] or '').strip() or None
    if 'currency' in data:
        vendor.currency = (data['currency'] or 'EUR').strip().upper()
    if 'website' in data:
        vendor.website = (data['website'] or '').strip() or None
    if 'active' in data:
        vendor.active = bool(data['active'])

    db.session.commit()

    cnt = Product.query.filter_by(vendor_id=vendor_id).count()
    return jsonify({'ok': True, 'vendor': _vendor_dict(vendor, cnt)})


# ---------------------------------------------------------------------------
# API — deactivate / reactivate
# ---------------------------------------------------------------------------

@vendors_bp.route('/api/v1/vendors/<int:vendor_id>', methods=['DELETE'], endpoint='api_vendor_toggle')
def api_vendor_toggle(vendor_id):
    """Toggle the vendor's active flag (soft delete / restore)."""
    vendor = Vendor.query.get_or_404(vendor_id)
    vendor.active = not vendor.active
    db.session.commit()

    cnt = Product.query.filter_by(vendor_id=vendor_id).count()
    return jsonify({'ok': True, 'vendor': _vendor_dict(vendor, cnt)})


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _vendor_dict(vendor, product_count: int) -> dict:
    """Serialise a Vendor ORM object to a JSON-safe dict."""
    return {
        'vendor_id':     vendor.vendor_id,
        'name':          vendor.name,
        'country':       vendor.country or '',
        'currency':      vendor.currency or 'EUR',
        'website':       vendor.website or '',
        'active':        vendor.active,
        'product_count': product_count,
        'flag':          VENDOR_FLAGS.get(vendor.country, ''),
    }


def _validate_vendor_data(data: dict, *, is_new: bool, current_vendor=None) -> list[str]:
    """Return a list of validation error messages (empty = valid)."""
    errors = []

    if is_new or 'name' in data:
        name = (data.get('name') or '').strip()
        if not name:
            errors.append('Vendor name is required.')
        else:
            # Check for duplicates, excluding the vendor being updated.
            q = Vendor.query.filter(func.lower(Vendor.name) == name.lower())
            if current_vendor:
                q = q.filter(Vendor.vendor_id != current_vendor.vendor_id)
            if q.first():
                errors.append(f'A vendor named "{name}" already exists.')

    if 'currency' in data:
        cur = (data.get('currency') or '').strip()
        if cur and len(cur) != 3:
            errors.append('Currency must be a 3-letter code (e.g. EUR, SEK, GBP).')

    return errors