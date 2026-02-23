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
    templates = InstrumentTemplate.query.order_by(InstrumentTemplate.name).all()

    return render_template(
        'templates/index.html',
        templates=templates,
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

    variants = sorted(t.variants, key=lambda v: (v.strings, v.scale_mm))

    return render_template(
        'templates/edit.html',
        t=t,
        variants=variants,
        errors=errors,
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


