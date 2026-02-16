from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Species(db.Model):
    __tablename__ = 'species'
    
    species_id = db.Column(db.Integer, primary_key=True)
    scientific_name = db.Column(db.String(100), unique=True, nullable=False)
    commercial_name = db.Column(db.String(100))
    cites_listed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    products = db.relationship('Product', back_populates='species')

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