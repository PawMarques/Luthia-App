"""
seed_templates.py
-----------------
Populates the instrument_templates and template_variants tables with
reference data for the predefined solid-body bass templates.

Run once after the main import:
    python3 seed_templates.py

Safe to re-run — existing records are updated, not duplicated.

Dimension notes
---------------
All dimensions are in mm and represent blank/rough stock sizes,
i.e. slightly larger than the finished instrument to allow for
shaping, routing and final planing.

Sources
-------
Jazz Bass body: blueprint-confirmed (525 × 350 × 45 mm)
P-Bass, Stingray, Spector NS: luthier forum / spec sheet references —
  flagged as reference-only until verified against a blueprint.

4-string 34" variants seeded for all templates.
5-string variants to be added in a future iteration.
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from models import db, InstrumentTemplate, TemplateVariant

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "tonewood.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


# =============================================================================
# TEMPLATE DEFINITIONS
# Each entry: (template_name, instrument_type, notes, [list of variant dicts])
# =============================================================================

TEMPLATES = [
    (
        'Jazz Bass',
        'bass',
        'Fender Jazz Bass — offset double-cutaway, asymmetric body. '
        'Blueprint-confirmed body dimensions (525×350×45 mm).',
        [
            {
                'label':                '4-string 34"',
                'strings':              4,
                'scale_mm':             863.6,
                # Body blank (blueprint-confirmed)
                'body_length_mm':       525.0,
                'body_width_mm':        350.0,
                'body_thickness_mm':    45.0,
                # Neck blank — bolt-on, nut to heel
                'neck_length_mm':       622.0,
                'neck_length_thru_mm':  None,
                # Neck profile
                'neck_thickness_1f_mm': 23.0,
                'neck_thickness_12f_mm':25.0,
                'nut_width_mm':         38.1,
                'neck_width_heel_mm':   62.0,
                # Headstock
                'headstock_length_mm':  185.0,
                'headstock_width_mm':   75.0,
                # Overall
                'overall_length_mm':    1185.0,
                # Flags
                'construction':         'bolt-on',
                'has_top':              False,
            },
        ],
    ),
    (
        'Precision Bass',
        'bass',
        'Fender Precision Bass — symmetrical double-cutaway slab body. '
        'Reference dimensions from luthier blueprints, not yet blueprint-confirmed.',
        [
            {
                'label':                '4-string 34"',
                'strings':              4,
                'scale_mm':             863.6,
                # Body blank (reference)
                'body_length_mm':       510.0,
                'body_width_mm':        335.0,
                'body_thickness_mm':    44.0,
                # Neck blank — bolt-on
                'neck_length_mm':       622.0,
                'neck_length_thru_mm':  None,
                # Neck profile
                'neck_thickness_1f_mm': 24.0,
                'neck_thickness_12f_mm':26.0,
                'nut_width_mm':         41.3,   # 1 5/8"
                'neck_width_heel_mm':   63.0,
                # Headstock
                'headstock_length_mm':  180.0,
                'headstock_width_mm':   75.0,
                # Overall
                'overall_length_mm':    1168.0,
                # Flags
                'construction':         'bolt-on',
                'has_top':              False,
            },
        ],
    ),
    (
        'Music Man Stingray',
        'bass',
        'Ernie Ball Music Man StingRay — compact body, 6-bolt neck, active EQ. '
        'Reference dimensions from luthier sources, not yet blueprint-confirmed.',
        [
            {
                'label':                '4-string 34"',
                'strings':              4,
                'scale_mm':             863.6,
                # Body blank (reference — notably more compact than Fender bodies)
                'body_length_mm':       445.0,
                'body_width_mm':        340.0,
                'body_thickness_mm':    44.0,
                # Neck blank — bolt-on
                'neck_length_mm':       622.0,
                'neck_length_thru_mm':  None,
                # Neck profile (standard nut, not SLO)
                'neck_thickness_1f_mm': 24.0,
                'neck_thickness_12f_mm':26.0,
                'nut_width_mm':         41.3,   # 1 5/8" standard
                'neck_width_heel_mm':   65.0,
                # Headstock — 3+1 configuration, slightly wider
                'headstock_length_mm':  175.0,
                'headstock_width_mm':   90.0,
                # Overall
                'overall_length_mm':    1150.0,
                # Flags
                'construction':         'bolt-on',
                'has_top':              False,
            },
        ],
    ),
    (
        'Spector NS',
        'bass',
        'Spector NS — carved/contoured body, neck-through construction, '
        'maple body wings. Reference dimensions from spec sheets.',
        [
            {
                'label':                '4-string 34"',
                'strings':              4,
                'scale_mm':             863.6,
                # Body blank — wings only (neck-through; blank is thicker due to deep carve)
                'body_length_mm':       460.0,
                'body_width_mm':        355.0,
                'body_thickness_mm':    50.0,   # extra thickness for carved contour
                # Neck-through blank — runs full instrument length
                'neck_length_mm':       None,   # not applicable for neck-through
                'neck_length_thru_mm':  950.0,  # nut to body tail end
                # Neck profile
                'neck_thickness_1f_mm': 21.0,
                'neck_thickness_12f_mm':24.0,
                'nut_width_mm':         41.7,   # 1.64" standard Spector
                'neck_width_heel_mm':   65.0,
                # Headstock
                'headstock_length_mm':  175.0,
                'headstock_width_mm':   75.0,
                # Overall
                'overall_length_mm':    1145.0,
                # Flags
                'construction':         'neck-through',
                'has_top':              True,   # maple cap is standard on NS
            },
        ],
    ),
]


def seed():
    with app.app_context():
        db.create_all()

        created_t = 0
        updated_t = 0
        created_v = 0
        updated_v = 0

        for tpl_name, tpl_type, tpl_notes, variants in TEMPLATES:

            # Upsert template
            tpl = InstrumentTemplate.query.filter_by(name=tpl_name).first()
            if not tpl:
                tpl = InstrumentTemplate(name=tpl_name)
                db.session.add(tpl)
                created_t += 1
            else:
                updated_t += 1

            tpl.instrument_type = tpl_type
            tpl.notes           = tpl_notes
            db.session.flush()   # ensure template_id is available

            for v in variants:
                label = v['label']
                variant = TemplateVariant.query.filter_by(
                    template_id=tpl.template_id, label=label
                ).first()

                if not variant:
                    variant = TemplateVariant(template_id=tpl.template_id, label=label)
                    db.session.add(variant)
                    created_v += 1
                else:
                    updated_v += 1

                # Apply all dimension fields
                for field, value in v.items():
                    if field != 'label':
                        setattr(variant, field, value)

        db.session.commit()

        print("\n" + "=" * 50)
        print("TEMPLATE SEED COMPLETE")
        print("=" * 50)
        print(f"  Templates : {created_t} created, {updated_t} updated")
        print(f"  Variants  : {created_v} created, {updated_v} updated")
        print()

        # Summary
        for tpl in InstrumentTemplate.query.order_by(InstrumentTemplate.template_id).all():
            print(f"  {tpl.name}  ({tpl.instrument_type})")
            for v in tpl.variants:
                neck_info = (
                    f"neck-thru {v.neck_length_thru_mm:.0f}mm"
                    if v.construction == 'neck-through'
                    else f"bolt-on neck {v.neck_length_mm:.0f}mm"
                )
                top_info = " + top" if v.has_top else ""
                print(
                    f"    [{v.label}]  "
                    f"body {v.body_length_mm:.0f}×{v.body_width_mm:.0f}×{v.body_thickness_mm:.0f}mm  "
                    f"{neck_info}  "
                    f"nut {v.nut_width_mm:.1f}mm{top_info}"
                )
        print()
        print("  Run python3 app.py to start the application.")
        print("=" * 50 + "\n")


if __name__ == '__main__':
    seed()
