"""Build planner routes and related API endpoints.

Provides:
  GET    /builds                              — list all saved builds
  GET    /builds/new                          — new build creation form
  POST   /builds/new                          — create a build from a template variant
  GET    /builds/<id>                         — build detail and part selection view
  GET    /api/builds/<id>/candidates/<role>   — candidate products for a part role
  PATCH  /api/builds/<id>/parts/<part_id>     — assign a product to a part slot
  DELETE /api/builds/<id>                     — delete a build and all its parts
"""

from datetime import datetime

from flask import Blueprint, jsonify, render_template, request

from helpers import ROLE_CATEGORIES, THICKNESS_WARN_LIMIT, VENDOR_FLAGS
from models import (
    Build, BuildPart, Category, InstrumentTemplate,
    Product, TemplateVariant, db,
)

builds_bp = Blueprint('builds', __name__)

# Emoji icon displayed next to each part role label in the build detail view.
_ROLE_ICONS = {'body': '🪵', 'neck': '🎸', 'fretboard': '📏', 'top': '✨'}


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

@builds_bp.route('/builds')
def builds_index():
    """Render the build planner index with a summary card for every saved build."""
    builds = Build.query.order_by(Build.updated_at.desc()).all()
    cards_html = ''.join(_build_card_html(b) for b in builds) or (
        '<p style="color:#52525b;text-align:center;padding:40px 0;">'
        'No builds yet. <a href="/builds/new" class="accent-link">Create your first one!</a></p>'
    )

    return render_template(
        'builds/index.html',
        cards_html=cards_html,
        active_nav='builds',
        breadcrumb=[('Build Planner', None)],
        page_title='Luthia · Build Planner',
    )


@builds_bp.route('/builds/new', methods=['GET', 'POST'])
def builds_new():
    """Show the new-build form on GET; create the build and redirect on POST."""
    error = None

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
                db.session.flush()  # Obtain build_id before creating child parts.

                for role in _roles_for_variant(variant):
                    db.session.add(BuildPart(build_id=build.build_id, role=role))

                db.session.commit()
                return f'<script>window.location="/builds/{build.build_id}"</script>'

    templates = InstrumentTemplate.query.order_by(InstrumentTemplate.name).all()

    # Lookup table used by the client-side variant dropdown to populate options
    # without a round-trip when the user changes the template selection.
    tpl_data = {
        t.template_id: [
            {
                'id':           v.variant_id,
                'label':        v.label,
                'construction': v.construction,
                'has_top':      v.has_top,
            }
            for v in t.variants
        ]
        for t in templates
    }

    tpl_opts = '<option value="">Select instrument…</option>' + ''.join(
        f'<option value="{t.template_id}">{t.name}</option>'
        for t in templates
    )

    return render_template(
        'builds/new.html',
        tpl_opts=tpl_opts,
        tpl_data=tpl_data,
        active_nav='builds',
        breadcrumb=[('Build Planner', '/builds'), ('New Build', None)],
        page_title='Luthia · New Build',
    )


@builds_bp.route('/builds/<int:build_id>')
def builds_detail(build_id):
    """Render the build detail page with part assignments and reference dimensions."""
    build   = Build.query.get_or_404(build_id)
    variant = build.variant

    parts_html, total = _render_parts(build)

    # Build the dimension reference panel shown alongside the part list.
    ref                = variant
    construction_label = ref.construction.replace('-', ' ').title()
    neck_len           = (
        ref.neck_length_thru_mm
        if ref.construction == 'neck-through'
        else ref.neck_length_mm
    )
    neck_label = (
        f'Neck-thru blank: {neck_len:.0f}mm'
        if ref.construction == 'neck-through'
        else f'Neck blank (nut→heel): {neck_len:.0f}mm'
    )

    # Warn when the instrument may not fit a standard hard case.
    case_warn = ''
    if ref.overall_length_mm and ref.overall_length_mm > 1250:
        case_warn += (
            ' <span style="color:#f59e0b;" '
            'title="Exceeds standard case length of 1250mm">⚠</span>'
        )
    if ref.body_width_mm and ref.body_width_mm > 380:
        case_warn += (
            ' <span style="color:#f59e0b;" '
            'title="Exceeds standard case width of 380mm">⚠</span>'
        )

    return render_template(
        'builds/detail.html',
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
# Build API
# ---------------------------------------------------------------------------

@builds_bp.route('/api/builds/<int:build_id>/candidates/<role>')
def api_build_candidates(build_id, role):
    """Return candidate products (JSON) suitable for a given part role in a build."""
    build      = Build.query.get_or_404(build_id)
    candidates = _candidate_products(role, build.variant)

    rows = []
    for c in candidates:
        p          = c['product']
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


@builds_bp.route('/api/builds/<int:build_id>/parts/<int:part_id>', methods=['PATCH'])
def api_build_part_update(build_id, part_id):
    """Assign a product to a build part slot and recompute all derived values."""
    build = Build.query.get_or_404(build_id)
    part  = BuildPart.query.filter_by(part_id=part_id, build_id=build_id).first_or_404()

    data       = request.get_json()
    product_id = data.get('product_id')
    part.product_id = product_id

    # Flag when the vendor hasn't published dimension data for this product.
    if product_id:
        p = Product.query.get(product_id)
        part.dims_unverified = not any([p.length_mm, p.width_mm, p.thickness_mm])
    else:
        part.dims_unverified = False

    _check_thickness_warning(build)
    build.compute_total()
    build.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'ok': True, 'total': build.total_price})


@builds_bp.route('/api/builds/<int:build_id>', methods=['DELETE'])
def api_build_delete(build_id):
    """Delete a build; BuildPart records are cascade-deleted by the ORM."""
    build = Build.query.get_or_404(build_id)
    db.session.delete(build)
    db.session.commit()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Business logic helpers
# ---------------------------------------------------------------------------

def _roles_for_variant(variant: TemplateVariant) -> list[str]:
    """Return the ordered list of part roles required for a given variant.

    A top blank slot is included only when the variant's design calls for one.
    """
    roles = ['body', 'neck', 'fretboard']
    if variant.has_top:
        roles.append('top')
    return roles


def _candidate_products(role: str, variant: TemplateVariant) -> list[dict]:
    """Return products suitable for the given build part role.

    Matching uses two tiers:
      Tier 1 (always)   — product category must match the role mapping.
      Tier 2 (optional) — dimension check applied only when the product has
                          dimension data on record; products without data pass
                          through but are flagged dims_unverified=True so the
                          builder knows to verify them before ordering.

    For neck-through builds, the full thru-neck length is compared instead of
    the shorter bolt-on nut-to-heel measurement.
    """
    cat_name = ROLE_CATEGORIES.get(role)
    if not cat_name:
        return []

    cat = Category.query.filter_by(name=cat_name).first()
    if not cat:
        return []

    products = (
        Product.query
        .filter_by(category_id=cat.category_id)
        .order_by(Product.price.asc())
        .all()
    )

    min_length, min_width, min_thickness = _minimum_dims_for_role(role, variant)

    results = []
    for p in products:
        has_dims = any([p.length_mm, p.width_mm, p.thickness_mm])
        dim_ok   = True  # Products without any dims pass through unflagged.

        if has_dims:
            if min_length    and p.length_mm    and p.length_mm    < min_length:    dim_ok = False
            if min_width     and p.width_mm     and p.width_mm     < min_width:     dim_ok = False
            if min_thickness and p.thickness_mm and p.thickness_mm < min_thickness: dim_ok = False

        if dim_ok:
            results.append({'product': p, 'dims_unverified': not has_dims})

    return results


def _minimum_dims_for_role(role: str, variant: TemplateVariant) -> tuple:
    """Return (min_length, min_width, min_thickness) in mm for the given role.

    Values are derived from the variant's blueprint dimensions.
    Returns (None, None, None) for unknown roles, which disables dimension
    filtering and includes all products in that category.
    """
    if role == 'body':
        return variant.body_length_mm, variant.body_width_mm, variant.body_thickness_mm

    if role == 'neck':
        # Use the neck-through length for NT builds; nut width is the narrowest
        # safe lower bound since the neck tapers from there to the heel.
        length = (
            variant.neck_length_thru_mm
            if variant.construction == 'neck-through'
            else variant.neck_length_mm
        )
        return length, variant.nut_width_mm, variant.neck_thickness_12f_mm

    if role == 'fretboard':
        # Fret 24 position ≈ scale × 0.75 from the nut (equal temperament).
        # Add 20 mm overhang for the nut slot and end trim.
        min_length = (variant.scale_mm or 864) * 0.75 + 20
        # Add 10 mm routing margin to the nut width for the board taper.
        min_width  = (variant.nut_width_mm or 38) + 10
        return min_length, min_width, 6.0  # 6 mm is the minimum usable blank thickness.

    if role == 'top':
        return variant.body_length_mm, variant.body_width_mm, 4.0  # Typical bookmatched top.

    return None, None, None


def _check_thickness_warning(build: Build) -> None:
    """Set thickness_warning on body and top parts when their combined thickness
    exceeds THICKNESS_WARN_LIMIT (45 mm).  Clears the flag otherwise.

    The warning reminds the builder to plane the body blank before final shaping
    so the instrument ends up at the correct finished thickness.
    """
    body_part = next((p for p in build.parts if p.role == 'body'), None)
    top_part  = next((p for p in build.parts if p.role == 'top'),  None)

    # If no top role exists for this variant, always clear body warning and return.
    if not body_part or not top_part:
        if body_part: body_part.thickness_warning = False
        if top_part:  top_part.thickness_warning  = False
        return

    body_t = body_part.product.thickness_mm if (body_part.product_id and body_part.product) else None
    top_t  = top_part.product.thickness_mm  if (top_part.product_id  and top_part.product)  else None

    warn = bool(body_t and top_t and (body_t + top_t) > THICKNESS_WARN_LIMIT)
    body_part.thickness_warning = warn
    top_part.thickness_warning  = warn


# ---------------------------------------------------------------------------
# HTML rendering helpers
# ---------------------------------------------------------------------------

def _build_card_html(b: Build) -> str:
    """Render a summary card for one build on the builds index page."""
    parts_done   = sum(1 for p in b.parts if p.product_id)
    parts_total  = len(b.parts)
    progress_pct = int(parts_done / parts_total * 100) if parts_total else 0
    price_str    = f'{b.total_price:,.0f} SEK' if b.total_price else '—'
    updated      = b.updated_at.strftime('%Y-%m-%d') if b.updated_at else ''
    warn_html    = (
        ' <span title="Thickness warning" style="color:#f59e0b;">⚠</span>'
        if any(p.thickness_warning for p in b.parts) else ''
    )

    return f"""
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


def _render_parts(build: Build) -> tuple[str, float]:
    """Render HTML for all parts in a build.  Returns (html_string, total_price)."""
    parts_html = ''
    total      = 0.0

    for part in build.parts:
        if part.product_id and part.product:
            html, price = _assigned_part_html(part)
            total += price
        else:
            html = _empty_part_html(part)
        parts_html += html

    return parts_html, total


def _assigned_part_html(part: BuildPart) -> tuple[str, float]:
    """Render the HTML row for a part that has a product assigned.

    Returns (html_string, price) so the caller can accumulate the build total.
    """
    p          = part.product
    role_label = part.role.capitalize()
    icon       = _ROLE_ICONS.get(part.role, '•')
    species    = p.species.commercial_name or p.species.scientific_name
    flag       = VENDOR_FLAGS.get(p.vendor.country, '')
    price      = p.price

    dims_parts = []
    if p.thickness_mm: dims_parts.append(f'{p.thickness_mm:.0f}mm thick')
    if p.width_mm:     dims_parts.append(f'{p.width_mm:.0f}mm wide')
    if p.length_mm:    dims_parts.append(f'{p.length_mm:.0f}mm long')
    dims_str = ' · '.join(dims_parts) if dims_parts else 'dimensions not specified'

    warn_html = ''
    if part.thickness_warning:
        warn_html += (
            '<div class="part-warning">'
            '⚠ Combined body + top thickness exceeds 45mm — body may need planing'
            '</div>'
        )
    if part.dims_unverified:
        warn_html += (
            '<div class="part-notice">'
            'ℹ Dimensions not specified by vendor — verify suitability before ordering'
            '</div>'
        )

    link_html  = (
        f'<a href="{p.product_url}" target="_blank" class="view-link" style="font-size:11px;">View ↗</a>'
        if p.product_url else ''
    )
    grade_html = f'<span class="badge-grade">{p.grade.name}</span>' if p.grade else ''

    html = f"""
<div class="part-row">
  <div class="part-role">{icon} {role_label}</div>
  <div class="part-detail">
    <div class="part-species">{species} {grade_html}</div>
    <div class="part-meta">{p.vendor.name} {flag} · {dims_str}</div>
    {warn_html}
  </div>
  <div class="part-price">{price:,.0f} <span style="color:#52525b;font-size:11px;">SEK</span></div>
  <div class="part-actions">
    {link_html}
    <button class="btn-sm" onclick="openPicker('{part.role}', {part.part_id})">Change</button>
  </div>
</div>"""

    return html, price


def _empty_part_html(part: BuildPart) -> str:
    """Render the HTML row for a part slot that has no product assigned yet."""
    role_label = part.role.capitalize()
    icon       = _ROLE_ICONS.get(part.role, '•')

    return f"""
<div class="part-row part-empty">
  <div class="part-role">{icon} {role_label}</div>
  <div class="part-detail" style="color:#52525b;">No product selected</div>
  <div class="part-price">—</div>
  <div class="part-actions">
    <button class="btn-select" onclick="openPicker('{part.role}', {part.part_id})">Select</button>
  </div>
</div>"""
