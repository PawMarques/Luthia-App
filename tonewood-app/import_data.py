import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from models import db, Species, Vendor, Category, Grade, Format, Unit, Product

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "tonewood.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def safe_float(value):
    """Convert value to float, handling ranges and special cases"""
    if pd.isna(value):
        return None
    
    value_str = str(value).strip().lower()
    
    # Handle empty or 'varies'
    if not value_str or value_str == 'varies' or value_str == 'nan':
        return None
    
    # Handle ranges like "40/45" or "7-8" - take the first number
    if '/' in value_str:
        value_str = value_str.split('/')[0]
    elif '-' in value_str and not value_str.startswith('-'):
        # Handle ranges like "7-8" but not negative numbers like "-5"
        parts = value_str.split('-')
        if len(parts) == 2 and parts[0].strip():
            value_str = parts[0]
    
    try:
        return float(value_str)
    except (ValueError, TypeError):
        return None

def import_basic_data():
    """Import categories and units first"""
    print("Setting up basic data...")
    
    categories = ['Body Blank', 'Neck Blank', 'Fretboard Blank', 'Top Blank', 'Carpentry lumber']
    for cat_name in categories:
        if not Category.query.filter_by(name=cat_name).first():
            cat = Category(name=cat_name)
            db.session.add(cat)
    
    units = ['per piece', 'per set', 'per kg', 'per m']
    for unit_name in units:
        if not Unit.query.filter_by(name=unit_name).first():
            unit = Unit(name=unit_name)
            db.session.add(unit)
    
    db.session.commit()
    print("âœ“ Basic data ready")

def import_species(file_path):
    """Import species from Excel"""
    print("Importing wood species...")
    
    df = pd.read_excel(file_path, sheet_name='Wood Species Complete', header=1)
    
    count = 0
    for _, row in df.iterrows():
        scientific_name = str(row['SCIENTIFIC NAME']).strip()
        
        if pd.isna(scientific_name) or scientific_name == 'nan':
            continue
            
        if Species.query.filter_by(scientific_name=scientific_name).first():
            continue
        
        commercial_name = str(row['COMMERCIAL NAME']).strip() if pd.notna(row['COMMERCIAL NAME']) else None
        
        species = Species(
            scientific_name=scientific_name,
            commercial_name=commercial_name
        )
        db.session.add(species)
        count += 1
    
    db.session.commit()
    print(f"âœ“ Imported {count} species")

def import_vendor_products(file_path, sheet_name, vendor_name, country):
    """Import products from a vendor sheet"""
    print(f"Importing {vendor_name}...")
    
    vendor = Vendor.query.filter_by(name=vendor_name).first()
    if not vendor:
        vendor = Vendor(name=vendor_name, country=country, currency='SEK')
        db.session.add(vendor)
        db.session.commit()
    
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=1)
    except Exception as e:
        print(f"  Error reading sheet: {e}")
        return
    
    count = 0
    skipped = 0

    def find_col(columns, keywords, required=True):
        """Find a column by searching for keywords (case-insensitive). 
        Returns the first match, or None if not found.
        Warns clearly if the column is required but missing."""
        for keyword in keywords:
            matches = [c for c in columns if keyword.lower() in c.lower()]
            if matches:
                return matches[0]
        if required:
            print(f"  ⚠️  WARNING: Could not find column matching {keywords} in sheet '{sheet_name}'")
            print(f"     Available columns: {list(columns)}")
        return None

    sci_col   = find_col(df.columns, ['scientific', 'latin'], required=True)
    price_col = find_col(df.columns, ['price (sek)', 'price (eur)'], required=True)
    length_col = find_col(df.columns, ['length'], required=False)

    if not sci_col or not price_col:
        print(f"  ✗ Skipping {sheet_name} — required columns missing.")
        return
    
    for _, row in df.iterrows():
        scientific_name = str(row[sci_col]).strip()
        
        if pd.isna(scientific_name) or scientific_name == 'nan':
            skipped += 1
            continue
        
        species = Species.query.filter_by(scientific_name=scientific_name).first()
        if not species:
            commercial = str(row[df.columns[1]]).strip() if pd.notna(row[df.columns[1]]) else None
            species = Species(scientific_name=scientific_name, commercial_name=commercial)
            db.session.add(species)
            db.session.flush()
            print(f"  Added missing species: {scientific_name}")
        
        if pd.isna(row['Category']):
            skipped += 1
            continue
            
        category_name = str(row['Category']).strip()
        category = Category.query.filter_by(name=category_name).first()
        if not category:
            category = Category(name=category_name)
            db.session.add(category)
            db.session.flush()
        
        grade = None
        if pd.notna(row['Grade']) and str(row['Grade']).strip():
            grade_name = str(row['Grade']).strip()
            grade = Grade.query.filter_by(name=grade_name).first()
            if not grade:
                grade = Grade(name=grade_name)
                db.session.add(grade)
                db.session.flush()
        
        format_obj = None
        if pd.notna(row['Format']) and str(row['Format']).strip():
            format_name = str(row['Format']).strip()
            format_obj = Format.query.filter_by(name=format_name).first()
            if not format_obj:
                format_obj = Format(name=format_name)
                db.session.add(format_obj)
                db.session.flush()
        
        unit = None
        if pd.notna(row['Unit']):
            unit_name = str(row['Unit']).strip()
            unit = Unit.query.filter_by(name=unit_name).first()
        
        # Get price with safe conversion
        price = safe_float(row[price_col])
        if price is None:
            skipped += 1
            continue
        
        # Handle dimensions with safe conversion
        thickness_mm = safe_float(row['Thickness (mm)'])
        width_mm = safe_float(row['Width (mm)'])
        
        # Handle length - convert meters to mm if needed
        length_value = safe_float(row[length_col]) if length_col else None
        if length_value and length_col and '(m)' in length_col and '(mm)' not in length_col:
            length_value = length_value * 1000
        
        weight_kg = safe_float(row['Weight (kg)'])
        
        # Create product
        product = Product(
            species_id=species.species_id,
            vendor_id=vendor.vendor_id,
            category_id=category.category_id,
            grade_id=grade.grade_id if grade else None,
            format_id=format_obj.format_id if format_obj else None,
            unit_id=unit.unit_id if unit else None,
            thickness_mm=thickness_mm,
            width_mm=width_mm,
            length_mm=length_value,
            weight_kg=weight_kg,
            price=price,
            currency='SEK' if price_col == 'Price (SEK)' else 'EUR',
            in_stock=str(row['In Stock']).lower() == 'yes' if pd.notna(row['In Stock']) else True,
            product_url=str(row['Product URL']) if pd.notna(row['Product URL']) else None
        )
        db.session.add(product)
        count += 1
    
    db.session.commit()
    print(f"âœ“ Imported {count} products ({skipped} skipped)")

def run_import():
    """Main import function"""
    
    print("\n" + "="*60)
    print("TONEWOOD DATA IMPORT")
    print("="*60)
    print("\nWhere is your Excel file?")
    print("1. In the data-sources folder (default)")
    print("2. Somewhere else")
    
    choice = input("\nEnter 1 or 2: ").strip()
    
    if choice == '2':
        file_path = input("Enter full path to Excel file: ").strip()
    else:
        # Default: look in ../data-sources relative to this script
        data_sources_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data-sources')
        data_sources_dir = os.path.normpath(data_sources_dir)
        
        xlsx_files = sorted([f for f in os.listdir(data_sources_dir) if f.endswith('.xlsx')]) if os.path.isdir(data_sources_dir) else []
        
        if not xlsx_files:
            print(f"\n  ✗ No .xlsx files found in: {data_sources_dir}")
            print("     Please check the folder exists and contains Excel files.")
            return
        
        print(f"\nFiles found in data-sources:")
        for i, fname in enumerate(xlsx_files, 1):
            print(f"  {i}. {fname}")
        
        file_choice = input(f"\nEnter number (1-{len(xlsx_files)}): ").strip()
        
        try:
            file_index = int(file_choice) - 1
            if not 0 <= file_index < len(xlsx_files):
                raise ValueError
        except ValueError:
            print("  ✗ Invalid choice. Aborting.")
            return
        
        file_path = os.path.join(data_sources_dir, xlsx_files[file_index])
    
    with app.app_context():
        db.create_all()
        
        print("\nStarting import...")
        print("-" * 60)
        
        import_basic_data()
        import_species(file_path)
        
        vendors = [
            ('Sunda Byggvaror', 'Sunda Byggvaror', 'Sweden'),
            ('Guitars & Woods', 'Guitars & Woods', 'Portugal'),
            ('Rivolta', 'Rivolta', 'Italy'),
            ('Forest Guitar Supplies', 'Forest Guitar Supplies', 'Spain')
        ]
        
        for sheet_name, vendor_name, country in vendors:
            try:
                import_vendor_products(file_path, sheet_name, vendor_name, country)
            except Exception as e:
                print(f"  Error importing {vendor_name}: {e}")
                import traceback
                traceback.print_exc()
        
        print("-" * 60)
        print("\nâœ… IMPORT COMPLETE!\n")
        print(f"Total species: {Species.query.count()}")
        print(f"Total vendors: {Vendor.query.count()}")
        print(f"Total products: {Product.query.count()}")
        print("\nYou can now run the website with: python3 app.py")
        print("="*60 + "\n")

if __name__ == '__main__':
    run_import()