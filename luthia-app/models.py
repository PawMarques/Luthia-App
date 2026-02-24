from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Species(db.Model):
    __tablename__ = 'species'
    
    species_id = db.Column(db.Integer, primary_key=True)
    scientific_name = db.Column(db.String(100), unique=True, nullable=False)
    commercial_name = db.Column(db.String(100))   # Default display name (English)
    alt_commercial_name = db.Column(db.String(100))
    english_name = db.Column(db.String(100))
    alt_english_name = db.Column(db.String(100))
    swedish_name = db.Column(db.String(100))
    alt_swedish_name = db.Column(db.String(100))
    portuguese_name = db.Column(db.String(100))
    alt_portuguese_name = db.Column(db.String(100))
    origin = db.Column(db.String(200))
    cites_listed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    products = db.relationship('Product', back_populates='species')
    aliases = db.relationship('SpeciesAlias', back_populates='species',
                               cascade='all, delete-orphan')

    def display_name(self):
        """Return the preferred display name: commercial > scientific."""
        return self.commercial_name or self.scientific_name


class SpeciesAlias(db.Model):
    """
    All known alternate names for a species, used during import to resolve
    vendor-listed names (e.g. 'Ask', 'Hard Maple', 'LÃ¶nn') to the canonical
    Species record.  Also serves as a searchable name index in the web UI.
    """
    __tablename__ = 'species_aliases'

    alias_id    = db.Column(db.Integer, primary_key=True)
    species_id  = db.Column(db.Integer, db.ForeignKey('species.species_id'),
                            nullable=False)
    alias_name  = db.Column(db.String(100), nullable=False)
    language    = db.Column(db.String(20))   # e.g. 'english', 'swedish', 'portuguese', 'vendor'
    source      = db.Column(db.String(50))   # e.g. 'species_sheet', 'vendor_sheet', 'manual'

    # Unique constraint: same alias can't appear twice for the same species
    __table_args__ = (
        db.UniqueConstraint('species_id', 'alias_name', name='uq_species_alias'),
    )

    species = db.relationship('Species', back_populates='aliases')

class Vendor(db.Model):
    __tablename__ = 'vendors'
    
    vendor_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    country = db.Column(db.String(50))
    currency = db.Column(db.String(3), default='SEK')
    website = db.Column(db.String(200))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    products = db.relationship('Product', back_populates='vendor')

class Category(db.Model):
    __tablename__ = 'categories'
    
    category_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    products = db.relationship('Product', back_populates='category')

class Grade(db.Model):
    __tablename__ = 'grades'
    
    grade_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    sort_order = db.Column(db.Integer)
    
    products = db.relationship('Product', back_populates='grade')

class Format(db.Model):
    __tablename__ = 'formats'
    
    format_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    products = db.relationship('Product', back_populates='format')

class Unit(db.Model):
    __tablename__ = 'units'
    
    unit_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    
    products = db.relationship('Product', back_populates='unit')

class ProductImage(db.Model):
    __tablename__ = 'product_images'

    image_id    = db.Column(db.Integer, primary_key=True)
    product_id  = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    source_type = db.Column(db.String(10), nullable=False, default='upload')  # 'upload' | 'url'
    filename    = db.Column(db.String(200))   # set for uploads
    url         = db.Column(db.String(500))   # set for external URLs
    caption     = db.Column(db.String(200))
    sort_order  = db.Column(db.Integer, default=0)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product', back_populates='images')


class Product(db.Model):
    __tablename__ = 'products'

    __table_args__ = (
        db.Index('ix_products_species_id',  'species_id'),
        db.Index('ix_products_vendor_id',   'vendor_id'),
        db.Index('ix_products_category_id', 'category_id'),
        db.Index('ix_products_price',       'price'),
    )

    product_id = db.Column(db.Integer, primary_key=True)
    species_id = db.Column(db.Integer, db.ForeignKey('species.species_id'), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.vendor_id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.category_id'), nullable=False)
    grade_id = db.Column(db.Integer, db.ForeignKey('grades.grade_id'))
    format_id = db.Column(db.Integer, db.ForeignKey('formats.format_id'))
    unit_id = db.Column(db.Integer, db.ForeignKey('units.unit_id'))
    
    species_as_listed = db.Column(db.String(100))
    thickness_mm = db.Column(db.Float)
    width_mm = db.Column(db.Float)
    length_mm = db.Column(db.Float)
    weight_kg = db.Column(db.Float)
    price = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='SEK')
    in_stock = db.Column(db.Boolean, default=True)
    product_url = db.Column(db.String(500))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    species = db.relationship('Species', back_populates='products')
    vendor = db.relationship('Vendor', back_populates='products')
    category = db.relationship('Category', back_populates='products')
    grade = db.relationship('Grade', back_populates='products')
    format = db.relationship('Format', back_populates='products')
    unit = db.relationship('Unit', back_populates='products')
    images = db.relationship('ProductImage', back_populates='product',
                             cascade='all, delete-orphan', order_by='ProductImage.sort_order')

# =============================================================================
# BUILD PLANNER TABLES
# =============================================================================

class InstrumentTemplate(db.Model):
    """
    A named instrument design (e.g. 'Jazz Bass', 'Precision Bass').
    Holds identity and type only — dimensions live in TemplateVariant.
    """
    __tablename__ = 'instrument_templates'

    template_id     = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(100), unique=True, nullable=False)
    instrument_type = db.Column(db.String(50), default='bass')  # 'bass', 'guitar' etc.
    notes           = db.Column(db.Text)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    variants = db.relationship('TemplateVariant', back_populates='template',
                               cascade='all, delete-orphan')
    builds   = db.relationship('Build', back_populates='template')


class TemplateVariant(db.Model):
    """
    A specific configuration of a template defined by string count and scale.
    Holds all the reference dimensions used to filter matching products.

    Body dimensions:
      body_length/width/thickness — blank dimensions (slightly larger than finished body)

    Neck dimensions:
      neck_length_mm      — nut to heel (bolt-on)
      neck_length_thru_mm — full blank length nut to body tail (neck-through)

    Construction:
      construction — 'bolt-on' or 'neck-through'
      has_top      — whether this variant typically uses a decorative top blank
    """
    __tablename__ = 'template_variants'

    variant_id    = db.Column(db.Integer, primary_key=True)
    template_id   = db.Column(db.Integer, db.ForeignKey('instrument_templates.template_id'),
                               nullable=False)
    label         = db.Column(db.String(100), nullable=False)  # e.g. '4-string 34"'
    strings       = db.Column(db.Integer, nullable=False, default=4)
    scale_mm      = db.Column(db.Float, nullable=False, default=864.0)  # 34" = 863.6 mm

    # Body blank dimensions (mm)
    body_length_mm    = db.Column(db.Float)
    body_width_mm     = db.Column(db.Float)
    body_thickness_mm = db.Column(db.Float)

    # Neck dimensions (mm)
    neck_length_mm        = db.Column(db.Float)  # bolt-on: nut to heel
    neck_length_thru_mm   = db.Column(db.Float)  # neck-through: nut to body tail
    neck_thickness_1f_mm  = db.Column(db.Float)  # thickness at 1st fret
    neck_thickness_12f_mm = db.Column(db.Float)  # thickness at 12th fret
    nut_width_mm          = db.Column(db.Float)
    neck_width_heel_mm    = db.Column(db.Float)  # width at heel / 24th fret end

    # Headstock dimensions (mm)
    headstock_length_mm = db.Column(db.Float)
    headstock_width_mm  = db.Column(db.Float)

    # Overall
    overall_length_mm = db.Column(db.Float)

    # Construction flags
    construction = db.Column(db.String(20), default='bolt-on')  # 'bolt-on' or 'neck-through'
    has_top      = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    template = db.relationship('InstrumentTemplate', back_populates='variants')
    builds   = db.relationship('Build', back_populates='variant')


class Build(db.Model):
    """
    A saved luthier build — links a user-named project to a template variant
    and holds the chosen products for each part role.
    """
    __tablename__ = 'builds'

    build_id    = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(150), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('instrument_templates.template_id'),
                             nullable=False)
    variant_id  = db.Column(db.Integer, db.ForeignKey('template_variants.variant_id'),
                             nullable=False)
    notes       = db.Column(db.Text)
    total_price = db.Column(db.Float)          # cached sum, recomputed on save
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    template = db.relationship('InstrumentTemplate', back_populates='builds')
    variant  = db.relationship('TemplateVariant',    back_populates='builds')
    parts    = db.relationship('BuildPart', back_populates='build',
                               cascade='all, delete-orphan')

    def compute_total(self):
        """Recompute and cache total_price from all assigned parts."""
        self.total_price = sum(
            p.product.price for p in self.parts if p.product_id is not None
        )
        return self.total_price


class BuildPart(db.Model):
    """
    One part slot in a build (body, neck, fretboard, top).
    product_id is nullable — a slot can exist before a product is chosen.

    Flags:
      thickness_warning — True if body + top combined thickness exceeds 45 mm
      dims_unverified   — True if matched product has no dimension data
    """
    __tablename__ = 'build_parts'

    part_id    = db.Column(db.Integer, primary_key=True)
    build_id   = db.Column(db.Integer, db.ForeignKey('builds.build_id'), nullable=False)
    role       = db.Column(db.String(20), nullable=False)
    # roles: 'body', 'neck', 'fretboard', 'top'

    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=True)
    notes      = db.Column(db.Text)

    # Warning flags (computed and stored at save time)
    thickness_warning = db.Column(db.Boolean, default=False)
    # True if body + top combined thickness > 45 mm
    dims_unverified   = db.Column(db.Boolean, default=False)
    # True if product has no dimension data (length/width/thickness all null)

    build   = db.relationship('Build',   back_populates='parts')
    product = db.relationship('Product')