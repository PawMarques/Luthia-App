"""Instrument template management routes.

Provides:
  GET  /templates            — list all templates and their dimension variants
  GET  /templates/<id>/edit  — template edit form
  POST /templates/<id>/edit  — save template name/type and all variant dimensions
"""

from flask import Blueprint, render_template, request

from models import InstrumentTemplate, TemplateVariant, db

templates_bp = Blueprint('templates', __name__)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@templates_bp.route('/templates')
def templates_index():
    """Render the template library with a summary card for each template."""
    templates  = InstrumentTemplate.query.order_by(InstrumentTemplate.name).all()
    cards_html = ''.join(_template_card_html(t) for t in templates) or (
        '<p style="color:#52525b;text-align:center;padding:40px 0;">No templates found.</p>'
    )

    return render_template(
        'templates/index.html',
        cards_html=cards_html,
        active_nav='templates',
        breadcrumb=[('Templates', None)],
        page_title='Luthia · Templates',
    )


@templates_bp.route('/templates/<int:template_id>/edit', methods=['GET', 'POST'])
def templates_edit(template_id):
    """Render the template edit form, or save changes on POST."""
    t      = InstrumentTemplate.query.get_or_404(template_id)
    errors = []

    if request.method == 'POST':
        errors = _save_template(t)
        if not errors:
            return '<script>window.location="/templates"</script>'

    variants_html = ''.join(
        _variant_edit_html(v)
        for v in sorted(t.variants, key=lambda v: (v.strings, v.scale_mm))
    )
    error_html = (
        '<div class="tpl-edit-error">' + '<br>'.join(errors) + '</div>'
        if errors else ''
    )

    return render_template(
        'templates/edit.html',
        t=t,
        variants_html=variants_html,
        error_html=error_html,
        active_nav='templates',
        breadcrumb=[('Templates', '/templates'), (f'Edit {t.name}', None)],
        page_title=f'Luthia · Templates · Edit {t.name}',
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _save_template(t: InstrumentTemplate) -> list[str]:
    """Validate and persist form data for a template and all its variants.

    Returns a list of error messages; empty list means the save succeeded.
    """
    errors = []
    name            = request.form.get('name', '').strip()
    instrument_type = request.form.get('instrument_type', '').strip().lower()
    notes           = request.form.get('notes', '').strip()

    if not name:
        errors.append('Template name is required.')
    elif name != t.name and InstrumentTemplate.query.filter_by(name=name).first():
        errors.append('A template with that name already exists.')

    if errors:
        return errors

    t.name            = name
    t.instrument_type = instrument_type or None
    t.notes           = notes or None

    for v in t.variants:
        _save_variant_fields(v)

    db.session.commit()
    return []


def _save_variant_fields(v: TemplateVariant) -> None:
    """Read variant dimension fields from the POST form and update the variant in-place."""
    prefix = f'v{v.variant_id}_'

    def _f(key):
        """Parse an optional numeric field; returns None for empty or invalid input."""
        raw = request.form.get(prefix + key, '').strip()
        try:
            return float(raw) if raw else None
        except ValueError:
            return None

    v.label        = request.form.get(f'{prefix}label', v.label).strip() or v.label
    v.strings      = int(request.form.get(f'{prefix}strings', v.strings) or v.strings)
    v.scale_mm     = float(request.form.get(f'{prefix}scale_mm', '') or v.scale_mm)
    v.construction = request.form.get(f'{prefix}construction', v.construction)
    v.has_top      = request.form.get(f'{prefix}has_top') == '1'

    v.body_length_mm        = _f('body_length_mm')
    v.body_width_mm         = _f('body_width_mm')
    v.body_thickness_mm     = _f('body_thickness_mm')
    v.neck_length_mm        = _f('neck_length_mm')
    v.neck_length_thru_mm   = _f('neck_length_thru_mm')
    v.nut_width_mm          = _f('nut_width_mm')
    v.neck_width_heel_mm    = _f('neck_width_heel_mm')
    v.neck_thickness_1f_mm  = _f('neck_thickness_1f_mm')
    v.neck_thickness_12f_mm = _f('neck_thickness_12f_mm')
    v.headstock_length_mm   = _f('headstock_length_mm')
    v.headstock_width_mm    = _f('headstock_width_mm')
    v.overall_length_mm     = _f('overall_length_mm')


def _template_card_html(t: InstrumentTemplate) -> str:
    """Render a summary card for one template on the template index page."""
    type_label   = t.instrument_type.capitalize() if t.instrument_type else 'Instrument'
    total_builds = len(t.builds)
    builds_note  = (
        f'<span class="tpl-builds-count">'
        f'{total_builds} build{"s" if total_builds != 1 else ""}</span>'
        if total_builds else ''
    )
    variants_html = ''.join(
        _variant_summary_html(v)
        for v in sorted(t.variants, key=lambda v: (v.strings, v.scale_mm))
    )
    variant_count = len(t.variants)

    return f"""
<div class="tpl-card">
  <div class="tpl-card-header">
    <div>
      <div class="tpl-card-title">{t.name}</div>
      <div class="tpl-card-type">{type_label} · {variant_count} variant{"s" if variant_count != 1 else ""}</div>
    </div>
    <div style="display:flex;align-items:center;gap:10px;">
      {builds_note}
      <a href="/templates/{t.template_id}/edit" class="btn-sm">Edit</a>
      <a href="/builds/new" class="btn-sm btn-sm--accent">New Build</a>
    </div>
  </div>
  {variants_html}
</div>"""


def _variant_summary_html(v: TemplateVariant) -> str:
    """Render the read-only dimension summary for one variant inside a template card."""
    construction_label = v.construction.replace('-', ' ').title() if v.construction else '—'
    has_top_badge      = ' <span class="badge-grade">+ Top</span>' if v.has_top else ''

    dim_rows = ''

    if v.body_length_mm:
        dim_rows += (
            f'<div class="tpl-dim-row"><span>Body blank</span>'
            f'<span>{v.body_length_mm:.0f} × {v.body_width_mm:.0f} × {v.body_thickness_mm:.0f} mm</span></div>'
        )

    if v.neck_length_mm or v.neck_length_thru_mm:
        # Show the thru-neck length for neck-through builds, bolt-on length otherwise.
        neck_len   = v.neck_length_thru_mm if v.construction == 'neck-through' else v.neck_length_mm
        neck_label = 'Neck blank (thru)' if v.construction == 'neck-through' else 'Neck blank'
        dim_rows  += (
            f'<div class="tpl-dim-row"><span>{neck_label}</span>'
            f'<span>{neck_len:.0f} mm</span></div>'
        )

    if v.nut_width_mm:
        dim_rows += (
            f'<div class="tpl-dim-row"><span>Nut width</span>'
            f'<span>{v.nut_width_mm:.1f} mm</span></div>'
        )

    if v.overall_length_mm:
        dim_rows += (
            f'<div class="tpl-dim-row"><span>Overall length</span>'
            f'<span>{v.overall_length_mm:.0f} mm</span></div>'
        )

    return f"""
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


def _variant_edit_html(v: TemplateVariant) -> str:
    """Render the edit form block for one variant inside the template edit page."""

    def fv(val):
        """Format a float for an HTML input value — blank string if None."""
        return '' if val is None else f'{val:g}'

    prefix   = f'v{v.variant_id}_'
    bolt_sel = 'selected' if v.construction == 'bolt-on'     else ''
    thru_sel = 'selected' if v.construction == 'neck-through' else ''
    top_chk  = 'checked'  if v.has_top else ''

    return f"""
<div class="tpl-edit-variant">
  <div class="tpl-edit-variant-title">Variant — {v.label}</div>

  <div class="tpl-edit-grid">
    <div class="form-group">
      <label class="filter-label">Label</label>
      <input type="text" name="{prefix}label" class="filter-input" value="{v.label}" required>
    </div>
    <div class="form-group">
      <label class="filter-label">Strings</label>
      <input type="number" name="{prefix}strings" class="filter-input" value="{v.strings}" min="1" max="12" required>
    </div>
    <div class="form-group">
      <label class="filter-label">Scale (mm)</label>
      <input type="number" name="{prefix}scale_mm" class="filter-input" value="{fv(v.scale_mm)}" step="0.1" required>
    </div>
    <div class="form-group">
      <label class="filter-label">Construction</label>
      <select name="{prefix}construction" class="filter-select">
        <option value="bolt-on" {bolt_sel}>Bolt-on</option>
        <option value="neck-through" {thru_sel}>Neck-through</option>
      </select>
    </div>
  </div>

  <div class="tpl-edit-section-label">Body Blank</div>
  <div class="tpl-edit-grid">
    <div class="form-group">
      <label class="filter-label">Length (mm)</label>
      <input type="number" name="{prefix}body_length_mm" class="filter-input" value="{fv(v.body_length_mm)}" step="0.1">
    </div>
    <div class="form-group">
      <label class="filter-label">Width (mm)</label>
      <input type="number" name="{prefix}body_width_mm" class="filter-input" value="{fv(v.body_width_mm)}" step="0.1">
    </div>
    <div class="form-group">
      <label class="filter-label">Thickness (mm)</label>
      <input type="number" name="{prefix}body_thickness_mm" class="filter-input" value="{fv(v.body_thickness_mm)}" step="0.1">
    </div>
    <div class="form-group">
      <label class="filter-label" style="display:flex;align-items:center;gap:8px;">
        <input type="checkbox" name="{prefix}has_top" value="1" {top_chk}
               class="accent-checkbox" style="width:14px;height:14px;">
        Includes top blank
      </label>
    </div>
  </div>

  <div class="tpl-edit-section-label">Neck Blank</div>
  <div class="tpl-edit-grid">
    <div class="form-group">
      <label class="filter-label">Length bolt-on (mm)</label>
      <input type="number" name="{prefix}neck_length_mm" class="filter-input" value="{fv(v.neck_length_mm)}" step="0.1">
    </div>
    <div class="form-group">
      <label class="filter-label">Length neck-thru (mm)</label>
      <input type="number" name="{prefix}neck_length_thru_mm" class="filter-input" value="{fv(v.neck_length_thru_mm)}" step="0.1">
    </div>
    <div class="form-group">
      <label class="filter-label">Nut width (mm)</label>
      <input type="number" name="{prefix}nut_width_mm" class="filter-input" value="{fv(v.nut_width_mm)}" step="0.1">
    </div>
    <div class="form-group">
      <label class="filter-label">Width at heel (mm)</label>
      <input type="number" name="{prefix}neck_width_heel_mm" class="filter-input" value="{fv(v.neck_width_heel_mm)}" step="0.1">
    </div>
    <div class="form-group">
      <label class="filter-label">Thickness at 1st fret (mm)</label>
      <input type="number" name="{prefix}neck_thickness_1f_mm" class="filter-input" value="{fv(v.neck_thickness_1f_mm)}" step="0.1">
    </div>
    <div class="form-group">
      <label class="filter-label">Thickness at 12th fret (mm)</label>
      <input type="number" name="{prefix}neck_thickness_12f_mm" class="filter-input" value="{fv(v.neck_thickness_12f_mm)}" step="0.1">
    </div>
  </div>

  <div class="tpl-edit-section-label">Headstock &amp; Overall</div>
  <div class="tpl-edit-grid">
    <div class="form-group">
      <label class="filter-label">Headstock length (mm)</label>
      <input type="number" name="{prefix}headstock_length_mm" class="filter-input" value="{fv(v.headstock_length_mm)}" step="0.1">
    </div>
    <div class="form-group">
      <label class="filter-label">Headstock width (mm)</label>
      <input type="number" name="{prefix}headstock_width_mm" class="filter-input" value="{fv(v.headstock_width_mm)}" step="0.1">
    </div>
    <div class="form-group">
      <label class="filter-label">Overall length (mm)</label>
      <input type="number" name="{prefix}overall_length_mm" class="filter-input" value="{fv(v.overall_length_mm)}" step="0.1">
    </div>
  </div>
</div>"""
