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