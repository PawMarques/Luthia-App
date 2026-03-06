"""Shared pytest fixtures for the Luthia test suite.

Fixtures in this file are automatically available to every test module.
The session-scoped ``app`` fixture creates one Flask application backed by an
in-memory SQLite database for the entire test run; ``db_session`` drops and
re-creates the schema around each individual test so tests are fully isolated;
``seed_db`` populates a minimal but realistic dataset that all integration
tests can rely on.
"""

import tempfile

import pytest
from sqlalchemy.pool import StaticPool

from app import create_app
from models import (
    Build,
    BuildPart,
    Category,
    Format,
    Grade,
    InstrumentTemplate,
    Product,
    Species,
    TemplateVariant,
    Vendor,
    db,
)


# ---------------------------------------------------------------------------
# Application and client
# ---------------------------------------------------------------------------

@pytest.fixture(scope='session')
def app():
    """Create a Flask application configured for testing.

    Uses an in-memory SQLite database with StaticPool so that all connections
    within the same test session share the same database (required for the test
    client to see data committed outside a request context).
    """
    upload_dir = tempfile.mkdtemp()

    application = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'connect_args': {'check_same_thread': False},
            'poolclass': StaticPool,
        },
        'UPLOAD_FOLDER': upload_dir,
    })

    # Push a single application context for the whole session so that ORM
    # operations in fixtures and helper code work without extra boilerplate.
    ctx = application.app_context()
    ctx.push()
    yield application
    ctx.pop()


@pytest.fixture
def client(app):
    """Return a Flask test client for sending HTTP requests in tests."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Database lifecycle
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session(app):
    """Set up fresh DB tables before each test and tear them down after.

    Calling ``db.create_all()`` / ``db.drop_all()`` around each test ensures
    that no state leaks between test functions even when they share the same
    in-memory database via StaticPool.
    """
    db.create_all()
    yield db
    db.session.remove()
    db.drop_all()


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

@pytest.fixture
def seed_db(db_session):
    """Insert a minimal but realistic dataset used by integration tests.

    Rows created
    ─────────────
    • 1 Vendor  (Nordic Woods, Sweden)
    • 1 Species (European Ash / Fraxinus excelsior)
    • 4 Categories: Body Blank, Neck Blank, Fretboard Blank, Top Blank
    • 1 Format  (Set)
    • 1 Grade   (AAA)
    • 2 Products in Body Blank at different prices (500 SEK / 800 SEK) so that
      filter and sort tests have meaningful results
    • 1 InstrumentTemplate + 1 TemplateVariant + 1 Build + 1 BuildPart
      so the builds routes can be exercised without any additional HTTP setup
    """
    # --- lookup tables -------------------------------------------------------
    vendor  = Vendor(name='Nordic Woods', country='Sweden', currency='SEK')
    species = Species(
        scientific_name='Fraxinus excelsior',
        commercial_name='European Ash',
    )
    cat_body      = Category(name='Body Blank')
    cat_neck      = Category(name='Neck Blank')
    cat_fretboard = Category(name='Fretboard Blank')
    cat_top       = Category(name='Top Blank')
    fmt   = Format(name='Set')
    grade = Grade(name='AAA', sort_order=1)

    for obj in (vendor, species, cat_body, cat_neck, cat_fretboard, cat_top, fmt, grade):
        db.session.add(obj)

    db.session.flush()  # populate PKs before creating FK-dependent rows

    # --- products ------------------------------------------------------------
    common = dict(
        species_id=species.species_id,
        vendor_id=vendor.vendor_id,
        category_id=cat_body.category_id,
        format_id=fmt.format_id,
        grade_id=grade.grade_id,
        currency='SEK',
        thickness_mm=50.0,
        width_mm=400.0,
        length_mm=500.0,
    )
    p1 = Product(**common, price=500.0)
    p2 = Product(**common, price=800.0)
    db.session.add(p1)
    db.session.add(p2)

    # --- instrument template -------------------------------------------------
    template = InstrumentTemplate(name='Jazz Bass', instrument_type='bass')
    db.session.add(template)
    db.session.flush()

    variant = TemplateVariant(
        template_id=template.template_id,
        label='4-string 34"',
        strings=4,
        scale_mm=864.0,
        construction='bolt-on',
        has_top=False,
        body_length_mm=480.0,
        body_width_mm=350.0,
        body_thickness_mm=45.0,
        neck_length_mm=640.0,
        nut_width_mm=38.0,
        # These three fields are formatted with "%.1f" in builds/detail.html;
        # they must be non-None or the Jinja template raises a TypeError.
        neck_width_heel_mm=65.0,
        neck_thickness_1f_mm=20.0,
        neck_thickness_12f_mm=22.5,
        overall_length_mm=1200.0,
    )
    db.session.add(variant)
    db.session.flush()

    build = Build(
        name='Test Build',
        template_id=template.template_id,
        variant_id=variant.variant_id,
    )
    db.session.add(build)
    db.session.flush()

    part = BuildPart(build_id=build.build_id, role='body')
    db.session.add(part)

    db.session.commit()

    yield {
        'vendor':    vendor,
        'species':   species,
        'categories': {
            'body':      cat_body,
            'neck':      cat_neck,
            'fretboard': cat_fretboard,
            'top':       cat_top,
        },
        'format':   fmt,
        'grade':    grade,
        'products': [p1, p2],
        'template': template,
        'variant':  variant,
        'build':    build,
        'part':     part,
    }
