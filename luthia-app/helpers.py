"""Shared display helpers and constants used across all route modules.

Single Responsibility: pure formatting + configuration constants only.
No Flask or SQLAlchemy imports here, so this module can be tested in isolation.
"""

from datetime import datetime, timezone

from flask import jsonify


# ---------------------------------------------------------------------------
# Display constants
# ---------------------------------------------------------------------------

# Maps category names to CSS badge classes used in the product table.
CATEGORY_CLASSES: dict[str, str] = {
    'Body Blank':         'cat-body',
    'Neck Blank':         'cat-neck',
    'Fretboard Blank':    'cat-fretboard',
    'Top Blank':          'cat-top',
    'Carpentry lumber':   'cat-carpentry',
    'Finished Fretboard': 'cat-finished',
}

# Maps vendor country names to emoji flags for display next to vendor names.
VENDOR_FLAGS: dict[str, str] = {
    'Sweden':   '🇸🇪',
    'Portugal': '🇵🇹',
    'Italy':    '🇮🇹',
    'Spain':    '🇪🇸',
}


# ---------------------------------------------------------------------------
# Build planner constants
# ---------------------------------------------------------------------------

# Combined body + top blank thickness above this limit (mm) triggers a warning
# reminding the builder they will need to plane the body blank down.
THICKNESS_WARN_LIMIT: float = 45.0

# Maps build-part role names to the product category they draw from.
ROLE_CATEGORIES: dict[str, str] = {
    'body':      'Body Blank',
    'neck':      'Neck Blank',
    'fretboard': 'Fretboard Blank',
    'top':       'Top Blank',
}


# ---------------------------------------------------------------------------
# Image upload constants
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({'jpg', 'jpeg', 'png', 'webp', 'gif'})


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

def paginate(query, page: int, per_page: int) -> dict:
    """Paginate a SQLAlchemy query and return a uniform result dict.

    Returns:
        items    — the ORM objects for the current page
        total    — total number of matching rows
        page     — the requested page number
        pages    — total number of pages (always ≥ 1)
        per_page — the page size used
    """
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        'items':    items,
        'total':    total,
        'page':     page,
        'pages':    max(1, (total + per_page - 1) // per_page),
        'per_page': per_page,
    }


def api_error(message, status=400):
    """Return a JSON error response with a normalised {ok, errors} shape."""
    msgs = message if isinstance(message, list) else [message]
    return jsonify({'ok': False, 'errors': msgs}), status


def allowed_file(filename: str) -> bool:
    """Return True if *filename* has an accepted image extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def staleness_color(age_months: float) -> str:
    """Return a hex colour reflecting how stale a price timestamp is.

    Green  (≤ 3 months) — recently updated
    Amber  (≤ 6 months) — getting stale
    Red    (> 6 months) — overdue for a refresh
    """
    if age_months <= 3:
        return '#34d399'
    if age_months <= 6:
        return '#f59e0b'
    return '#f87171'


def staleness_info(last_updated) -> tuple[str, str]:
    """Return (date_string, colour_hex) for a last_updated datetime.

    Returns ('', muted_grey) when no date is recorded so callers
    never need to guard against None before rendering.
    """
    if not last_updated:
        return '', '#3f3f46'
    age_months = (datetime.now(timezone.utc).replace(tzinfo=None) - last_updated).days / 30.4
    return last_updated.strftime('%Y-%m-%d'), staleness_color(age_months)


def fmt_dims(product) -> str:
    """Format T × W × L dimensions from a Product as a human-readable string.

    Only includes dimensions that are set; returns '' when none are recorded.
    """
    parts = []
    if product.thickness_mm: parts.append(f'{product.thickness_mm:g}')
    if product.width_mm:     parts.append(f'{product.width_mm:g}')
    if product.length_mm:    parts.append(f'{product.length_mm:g}')
    return (' × '.join(parts) + ' mm') if parts else ''


def fmt_image(img) -> dict:
    """Serialise a ProductImage ORM object to a plain dict for JSON API responses."""
    src = (
        f'/uploads/{img.filename}'
        if img.source_type == 'upload'
        else img.url or ''
    )
    return {
        'image_id':    img.image_id,
        'source_type': img.source_type,
        'src':         src,
        'caption':     img.caption or '',
        'sort_order':  img.sort_order,
    }
