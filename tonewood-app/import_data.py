import pandas as pd
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from models import db, Species, SpeciesAlias, Vendor, Category, Grade, Format, Unit, Product

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "tonewood.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Sheet name for species reference - skipped when detecting vendor sheets
SPECIES_SHEET = 'Wood Species Complete'


def safe_float(value):
    """Convert value to float, handling ranges and special cases"""
    if pd.isna(value):
        return None

    value_str = str(value).strip().lower()

    if not value_str or value_str == 'varies' or value_str == 'nan':
        return None

    # Handle ranges like "40/45" - take the first number
    if '/' in value_str:
        value_str = value_str.split('/')[0]
    elif '-' in value_str and not value_str.startswith('-'):
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
            db.session.add(Category(name=cat_name))

    units = ['per piece', 'per set', 'per kg', 'per m']
    for unit_name in units:
        if not Unit.query.filter_by(name=unit_name).first():
            db.session.add(Unit(name=unit_name))

    db.session.commit()
    print("  Done")


def _safe_str(value):
    """Return stripped string or None for NaN/empty values."""
    if pd.isna(value):
        return None
    s = str(value).strip()
    return s if s and s.lower() != 'nan' else None


def _add_alias(species, alias_name, language, source='species_sheet'):
    """Add an alias for a species if not already present."""
    if not alias_name:
        return
    exists = SpeciesAlias.query.filter_by(
        species_id=species.species_id, alias_name=alias_name
    ).first()
    if not exists:
        db.session.add(SpeciesAlias(
            species_id=species.species_id,
            alias_name=alias_name,
            language=language,
            source=source,
        ))


def import_species(species_file_path):
    """
    Import species from the dedicated species reference Excel file.
    Populates all name columns on Species and builds the SpeciesAlias table.
    Skips gracefully if the sheet is not present.
    """
    xl = pd.ExcelFile(species_file_path)
    if SPECIES_SHEET not in xl.sheet_names:
        print(f"  No '{SPECIES_SHEET}' sheet found - skipping species pre-load.")
        print(f"  (Species will still be added automatically from vendor sheets.)")
        return

    print("Importing wood species and aliases...")
    df = pd.read_excel(species_file_path, sheet_name=SPECIES_SHEET, header=1)

    # Column name map — tolerant of minor variations
    col = {}
    for c in df.columns:
        cl = c.strip().upper()
        if 'SCIENTIFIC' in cl:           col['sci']      = c
        elif cl == 'COMMERCIAL NAME':    col['comm']     = c
        elif 'ALT. COMMERCIAL' in cl:    col['alt_comm'] = c
        elif cl == 'ENGLISH':            col['en']       = c
        elif 'ALT. ENGLISH' in cl:       col['alt_en']   = c
        elif cl == 'SWEDISH':            col['sv']       = c
        elif 'ALT. SWEDISH' in cl:       col['alt_sv']   = c
        elif cl == 'PORTUGUESE':         col['pt']       = c
        elif 'ALT. PORTUGUESE' in cl:    col['alt_pt']   = c
        elif 'ORIGIN' in cl:             col['origin']   = c
        elif 'CITES' in cl:              col['cites']    = c

    count_new = 0
    count_updated = 0

    for _, row in df.iterrows():
        scientific_name = _safe_str(row.get(col.get('sci', ''), None))
        if not scientific_name:
            continue

        commercial_name    = _safe_str(row.get(col.get('comm', ''),     None))
        alt_commercial     = _safe_str(row.get(col.get('alt_comm', ''), None))
        english_name       = _safe_str(row.get(col.get('en', ''),       None))
        alt_english        = _safe_str(row.get(col.get('alt_en', ''),   None))
        swedish_name       = _safe_str(row.get(col.get('sv', ''),       None))
        alt_swedish        = _safe_str(row.get(col.get('alt_sv', ''),   None))
        portuguese_name    = _safe_str(row.get(col.get('pt', ''),       None))
        alt_portuguese     = _safe_str(row.get(col.get('alt_pt', ''),   None))
        origin             = _safe_str(row.get(col.get('origin', ''),   None))
        cites_raw          = _safe_str(row.get(col.get('cites', ''),    None))
        cites_listed       = bool(cites_raw) if cites_raw else False

        species = Species.query.filter_by(scientific_name=scientific_name).first()

        if not species:
            species = Species(scientific_name=scientific_name)
            db.session.add(species)
            db.session.flush()   # get species_id before adding aliases
            count_new += 1
        else:
            count_updated += 1

        # Update all name fields
        species.commercial_name    = commercial_name    or species.commercial_name
        species.alt_commercial_name= alt_commercial     or species.alt_commercial_name
        species.english_name       = english_name       or species.english_name
        species.alt_english_name   = alt_english        or species.alt_english_name
        species.swedish_name       = swedish_name       or species.swedish_name
        species.alt_swedish_name   = alt_swedish        or species.alt_swedish_name
        species.portuguese_name    = portuguese_name    or species.portuguese_name
        species.alt_portuguese_name= alt_portuguese     or species.alt_portuguese_name
        species.origin             = origin             or species.origin
        species.cites_listed       = cites_listed

        # Register every non-null name as a searchable alias
        _add_alias(species, commercial_name,  'english',    'species_sheet')
        _add_alias(species, alt_commercial,   'english',    'species_sheet')
        _add_alias(species, english_name,     'english',    'species_sheet')
        _add_alias(species, alt_english,      'english',    'species_sheet')
        _add_alias(species, swedish_name,     'swedish',    'species_sheet')
        _add_alias(species, alt_swedish,      'swedish',    'species_sheet')
        _add_alias(species, portuguese_name,  'portuguese', 'species_sheet')
        _add_alias(species, alt_portuguese,   'portuguese', 'species_sheet')

    db.session.commit()
    print(f"  {count_new} new species, {count_updated} updated")
    alias_count = SpeciesAlias.query.count()
    print(f"  {alias_count} aliases registered")


def build_alias_lookup():
    """
    Return a dict mapping every known alias name (case-insensitive) to its
    Species object.  Used during product import to resolve vendor-listed names.
    Also includes scientific names as keys for direct lookup.
    """
    lookup = {}
    for species in Species.query.all():
        lookup[species.scientific_name.lower()] = species
        if species.commercial_name:
            lookup[species.commercial_name.lower()] = species
    for alias in SpeciesAlias.query.all():
        lookup[alias.alias_name.lower()] = alias.species
    return lookup


def parse_vendor_info(sheet_name, file_path):
    """Extract vendor name and country from the title banner in row 0.

    Expects a title like: 'GUITARS & WOODS (Portugal)'
    Returns (vendor_name, country). Falls back to sheet name and None if unexpected format.
    """
    try:
        raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None, nrows=1)
        title = str(raw.iloc[0, 0]).strip()

        country_match = re.search(r'\(([^)]+)\)', title)
        country = country_match.group(1).strip() if country_match else None

        name_part = re.split(r'\s*[-\(]', title)[0].strip().title()

        if not name_part or name_part.lower() == 'nan':
            return sheet_name, country

        return name_part, country

    except Exception:
        return sheet_name, None


def detect_vendor_sheets(file_path):
    """Return all sheet names that are vendor sheets (i.e. not the species sheet)."""
    xl = pd.ExcelFile(file_path)
    return [s for s in xl.sheet_names if s != SPECIES_SHEET]


def generate_diff(file_path, sheet_name):
    """Compare Excel sheet against current DB for one vendor.

    Matches products by URL where available, falls back to a composite key
    (vendor + species + category + format) for rows without a URL.

    Returns a dict with keys: new, removed, price_changes, stock_changes.
    Each entry is a list of dicts describing the change.
    """
    vendor_name, _ = parse_vendor_info(sheet_name, file_path)
    vendor = Vendor.query.filter_by(name=vendor_name).first()

    diff = {'new': [], 'removed': [], 'price_changes': [], 'stock_changes': []}

    # --- Load Excel rows into a normalised dict keyed by URL or composite ---
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=1)
    except Exception as e:
        print(f"  Could not read sheet for diff: {e}")
        return diff

    def find_col(columns, keywords):
        for keyword in keywords:
            matches = [c for c in columns if keyword.lower() in c.lower()]
            if matches:
                return matches[0]
        return None

    sci_col   = find_col(df.columns, ['scientific', 'latin'])
    price_col = find_col(df.columns, ['price (sek)', 'price (eur)'])

    if not sci_col or not price_col:
        return diff

    excel_by_url = {}       # url -> row dict  (for rows that have a URL)
    excel_no_url = []       # list of row dicts (for rows without a URL)

    for _, row in df.iterrows():
        scientific_name = str(row[sci_col]).strip()
        if pd.isna(scientific_name) or scientific_name == 'nan':
            continue

        price = safe_float(row[price_col])
        if price is None:
            continue

        category = str(row['Category']).strip() if pd.notna(row['Category']) else ''
        format_name = str(row['Format']).strip() if pd.notna(row['Format']) else ''
        in_stock = str(row['In Stock']).lower() == 'yes' if pd.notna(row['In Stock']) else True
        url = str(row['Product URL']).strip() if pd.notna(row['Product URL']) else ''

        label = f"{scientific_name} | {category} | {format_name or '-'} | {price:.2f} SEK"

        entry = {
            'species': scientific_name,
            'category': category,
            'format': format_name,
            'price': price,
            'in_stock': in_stock,
            'url': url,
            'label': label,
        }

        if url:
            excel_by_url[url] = entry
        else:
            excel_no_url.append(entry)

    # --- Load DB products for this vendor ---
    if not vendor:
        # No vendor in DB yet - everything in Excel is new
        for entry in list(excel_by_url.values()) + excel_no_url:
            diff['new'].append({'label': entry['label'], 'url': entry['url']})
        return diff

    db_products = Product.query.filter_by(vendor_id=vendor.vendor_id).all()

    db_by_url = {}      # url -> Product
    db_no_url = []      # Products without URL

    for p in db_products:
        if p.product_url:
            db_by_url[p.product_url] = p
        else:
            db_no_url.append(p)

    # --- Compare URL-matched products ---
    for url, excel_row in excel_by_url.items():
        if url not in db_by_url:
            diff['new'].append({'label': excel_row['label'], 'url': url})
        else:
            db_p = db_by_url[url]
            species_name = db_p.species.commercial_name or db_p.species.scientific_name
            change_label = (f"{species_name} | "
                           f"{db_p.category.name} | "
                           f"{db_p.format.name if db_p.format else '-'}")

            if abs((db_p.price or 0) - excel_row['price']) > 0.01:
                diff['price_changes'].append({
                    'label': change_label,
                    'old_price': db_p.price,
                    'new_price': excel_row['price'],
                    'url': url,
                })

            db_in_stock = db_p.in_stock if db_p.in_stock is not None else True
            if db_in_stock != excel_row['in_stock']:
                diff['stock_changes'].append({
                    'label': change_label,
                    'old_stock': 'In stock' if db_in_stock else 'Out of stock',
                    'new_stock': 'In stock' if excel_row['in_stock'] else 'Out of stock',
                    'url': url,
                })

    # Removed = in DB but URL not in Excel
    for url, db_p in db_by_url.items():
        if url not in excel_by_url:
            species_name = db_p.species.commercial_name or db_p.species.scientific_name
            diff['removed'].append({
                'label': (f"{species_name} | "
                         f"{db_p.category.name} | "
                         f"{db_p.format.name if db_p.format else '-'}"),
                'url': url,
            })

    # --- Compare no-URL products by composite key ---
    def composite_key(species, category, format_name):
        return f"{species}|{category}|{format_name}"

    db_no_url_keys = {
        composite_key(
            p.species.scientific_name,
            p.category.name,
            p.format.name if p.format else ''
        ): p
        for p in db_no_url
    }

    for entry in excel_no_url:
        key = composite_key(entry['species'], entry['category'], entry['format'])
        if key not in db_no_url_keys:
            diff['new'].append({'label': entry['label'], 'url': ''})
        else:
            db_p = db_no_url_keys[key]
            species_name = db_p.species.commercial_name or db_p.species.scientific_name
            change_label = (f"{species_name} | "
                           f"{db_p.category.name} | "
                           f"{db_p.format.name if db_p.format else '-'}")

            if abs((db_p.price or 0) - entry['price']) > 0.01:
                diff['price_changes'].append({
                    'label': change_label,
                    'old_price': db_p.price,
                    'new_price': entry['price'],
                    'url': '',
                })

            db_in_stock = db_p.in_stock if db_p.in_stock is not None else True
            if db_in_stock != entry['in_stock']:
                diff['stock_changes'].append({
                    'label': change_label,
                    'old_stock': 'In stock' if db_in_stock else 'Out of stock',
                    'new_stock': 'In stock' if entry['in_stock'] else 'Out of stock',
                    'url': '',
                })

    for key, db_p in db_no_url_keys.items():
        excel_keys = {
            composite_key(e['species'], e['category'], e['format'])
            for e in excel_no_url
        }
        if key not in excel_keys:
            species_name = db_p.species.commercial_name or db_p.species.scientific_name
            diff['removed'].append({
                'label': (f"{species_name} | "
                         f"{db_p.category.name} | "
                         f"{db_p.format.name if db_p.format else '-'}"),
                'url': '',
            })

    return diff


def print_diff(vendor_name, diff):
    """Print a formatted diff report for one vendor."""
    new      = diff['new']
    removed  = diff['removed']
    prices   = diff['price_changes']
    stock    = diff['stock_changes']

    total = len(new) + len(removed) + len(prices) + len(stock)

    print(f"\n  {vendor_name}:")

    if total == 0:
        print("    No changes detected")
        return

    if new:
        print(f"    + {len(new)} new product(s):")
        for item in new[:5]:
            print(f"        {item['label']}")
        if len(new) > 5:
            print(f"        ... and {len(new) - 5} more")

    if removed:
        print(f"    - {len(removed)} removed product(s):")
        for item in removed[:5]:
            print(f"        {item['label']}")
        if len(removed) > 5:
            print(f"        ... and {len(removed) - 5} more")

    if prices:
        print(f"    ~ {len(prices)} price change(s):")
        for item in prices[:5]:
            direction = "up" if item['new_price'] > item['old_price'] else "down"
            print(f"        {item['label']}")
            print(f"            {item['old_price']:.2f} -> {item['new_price']:.2f} SEK ({direction})")
        if len(prices) > 5:
            print(f"        ... and {len(prices) - 5} more")

    if stock:
        print(f"    ~ {len(stock)} stock change(s):")
        for item in stock[:5]:
            print(f"        {item['label']}")
            print(f"            {item['old_stock']} -> {item['new_stock']}")
        if len(stock) > 5:
            print(f"        ... and {len(stock) - 5} more")


def import_vendor_products(file_path, sheet_name, alias_lookup=None):
    """Import products from a vendor sheet, extracting vendor info from the title banner.
    
    alias_lookup: dict mapping lowercase name -> Species, built by build_alias_lookup().
                  If None, falls back to direct scientific name query only.
    """
    if alias_lookup is None:
        alias_lookup = build_alias_lookup()

    vendor_name, country = parse_vendor_info(sheet_name, file_path)
    print(f"Importing {vendor_name} ({country or 'country unknown'})...")

    vendor = Vendor.query.filter_by(name=vendor_name).first()
    if not vendor:
        vendor = Vendor(name=vendor_name, country=country, currency='SEK')
        db.session.add(vendor)
        db.session.commit()
    elif country and vendor.country != country:
        vendor.country = country
        db.session.commit()

    # Clear existing products for this vendor before re-importing
    Product.query.filter_by(vendor_id=vendor.vendor_id).delete()
    db.session.commit()

    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=1)
    except Exception as e:
        print(f"  Error reading sheet: {e}")
        return

    count = 0
    skipped = 0

    def find_col(columns, keywords, required=True):
        for keyword in keywords:
            matches = [c for c in columns if keyword.lower() in c.lower()]
            if matches:
                return matches[0]
        if required:
            print(f"  WARNING: Could not find column matching {keywords} in sheet '{sheet_name}'")
            print(f"  Available columns: {list(columns)}")
        return None

    sci_col    = find_col(df.columns, ['scientific', 'latin'], required=True)
    price_col  = find_col(df.columns, ['price (sek)', 'price (eur)'], required=True)
    length_col = find_col(df.columns, ['length'], required=False)
    listed_col = find_col(df.columns, ['as listed', 'listed'], required=False)

    if not sci_col or not price_col:
        print(f"  Skipping {sheet_name} - required columns missing.")
        return

    for _, row in df.iterrows():
        scientific_name = str(row[sci_col]).strip()

        if pd.isna(scientific_name) or scientific_name == 'nan':
            skipped += 1
            continue

        # --- Resolve species ---
        # 1. Try scientific name via alias lookup (covers direct scientific match too)
        species = alias_lookup.get(scientific_name.lower())

        # 2. Try 'as listed' name via alias lookup
        listed_name = None
        if listed_col and pd.notna(row[listed_col]):
            listed_name = str(row[listed_col]).strip()
            if not species and listed_name:
                species = alias_lookup.get(listed_name.lower())

        # 3. Fall back: create a new species record from scientific name
        if not species:
            commercial = _safe_str(row[df.columns[1]]) if len(df.columns) > 1 else None
            species = Species(scientific_name=scientific_name, commercial_name=commercial)
            db.session.add(species)
            db.session.flush()
            print(f"  Added unrecognised species: {scientific_name}")
            # Add to lookup so subsequent rows with same name don't create duplicates
            alias_lookup[scientific_name.lower()] = species

        # 4. Register the vendor's listed name as a vendor alias if it's new
        if listed_name and listed_name.lower() not in alias_lookup:
            _add_alias(species, listed_name, 'vendor', source='vendor_sheet')
            db.session.flush()
            alias_lookup[listed_name.lower()] = species

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

        price = safe_float(row[price_col])
        if price is None:
            skipped += 1
            continue

        thickness_mm = safe_float(row['Thickness (mm)'])
        width_mm = safe_float(row['Width (mm)'])

        length_value = safe_float(row[length_col]) if length_col else None
        if length_value and length_col and '(m)' in length_col and '(mm)' not in length_col:
            length_value = length_value * 1000

        weight_kg = safe_float(row['Weight (kg)'])

        # Read Last Updated from Excel, fall back to now if missing or unparseable
        last_updated = None
        if 'Last Updated' in df.columns and pd.notna(row['Last Updated']):
            try:
                last_updated = pd.to_datetime(row['Last Updated']).to_pydatetime()
            except Exception:
                pass
        if last_updated is None:
            from datetime import datetime
            last_updated = datetime.utcnow()

        product = Product(
            species_id=species.species_id,
            vendor_id=vendor.vendor_id,
            category_id=category.category_id,
            grade_id=grade.grade_id if grade else None,
            format_id=format_obj.format_id if format_obj else None,
            unit_id=unit.unit_id if unit else None,
            species_as_listed=listed_name or scientific_name,
            thickness_mm=thickness_mm,
            width_mm=width_mm,
            length_mm=length_value,
            weight_kg=weight_kg,
            price=price,
            currency='SEK' if 'sek' in price_col.lower() else 'EUR',
            in_stock=str(row['In Stock']).lower() == 'yes' if pd.notna(row['In Stock']) else True,
            product_url=str(row['Product URL']) if pd.notna(row['Product URL']) else None,
            last_updated=last_updated
        )
        db.session.add(product)
        count += 1

    db.session.commit()
    print(f"  {count} products imported ({skipped} skipped)")


def run_import():
    """Main import function"""

    print("\n" + "="*60)
    print("TONEWOOD DATA IMPORT")
    print("="*60)
    print("\nWhere are your Excel files?")
    print("1. In the data-sources folder (default)")
    print("2. Specify paths manually")

    choice = input("\nEnter 1 or 2: ").strip()

    if choice == '2':
        suppliers_file = input("Enter full path to suppliers Excel file: ").strip()
        species_file   = input("Enter full path to species Excel file (or press Enter to skip): ").strip()
        species_file   = species_file or None
    else:
        data_sources_dir = os.path.normpath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data-sources')
        )

        xlsx_files = sorted(
            [f for f in os.listdir(data_sources_dir) if f.endswith('.xlsx')]
        ) if os.path.isdir(data_sources_dir) else []

        if not xlsx_files:
            print(f"\n  No .xlsx files found in: {data_sources_dir}")
            print("  Please check the folder exists and contains Excel files.")
            return

        print(f"\nFiles found in data-sources:")
        for i, fname in enumerate(xlsx_files, 1):
            print(f"  {i}. {fname}")

        # Suppliers file
        sup_choice = input(f"\nEnter number for SUPPLIERS file (1-{len(xlsx_files)}): ").strip()
        try:
            sup_index = int(sup_choice) - 1
            if not 0 <= sup_index < len(xlsx_files):
                raise ValueError
        except ValueError:
            print("  Invalid choice. Aborting.")
            return
        suppliers_file = os.path.join(data_sources_dir, xlsx_files[sup_index])

        # Species file (optional, auto-detect if only one other xlsx)
        others = [f for i, f in enumerate(xlsx_files) if i != sup_index]
        if others:
            print(f"\nSpecies reference files:")
            for i, fname in enumerate(others, 1):
                print(f"  {i}. {fname}")
            sp_choice = input(f"Enter number for SPECIES file (or press Enter to skip): ").strip()
            if sp_choice:
                try:
                    sp_index = int(sp_choice) - 1
                    if not 0 <= sp_index < len(others):
                        raise ValueError
                    species_file = os.path.join(data_sources_dir, others[sp_index])
                except ValueError:
                    print("  Invalid choice, skipping species file.")
                    species_file = None
            else:
                species_file = None
        else:
            species_file = None

        file_path = suppliers_file  # keep for diff report

    with app.app_context():
        db.create_all()

        vendor_sheets = detect_vendor_sheets(suppliers_file)

        # --- Diff report ---
        print("\n" + "="*60)
        print("CHANGE REPORT")
        print("="*60)

        all_diffs = {}
        any_changes = False

        for sheet_name in vendor_sheets:
            vendor_name, _ = parse_vendor_info(sheet_name, suppliers_file)
            diff = generate_diff(suppliers_file, sheet_name)
            all_diffs[sheet_name] = diff
            print_diff(vendor_name, diff)

            if any(diff[k] for k in diff):
                any_changes = True

        if not any_changes:
            print("\n  Database is already up to date.")

        # --- Confirm before proceeding ---
        print("\n" + "="*60)
        confirm = input("Proceed with import? (y/n): ").strip().lower()
        if confirm != 'y':
            print("  Import cancelled.")
            return

        # --- Run import ---
        print("\nStarting import...")
        print("-" * 60)

        import_basic_data()

        # Import species reference first (builds the alias table)
        if species_file:
            import_species(species_file)
        else:
            print("  No species file provided - aliases will be built from vendor data only.")

        # Build alias lookup once for all vendor imports
        alias_lookup = build_alias_lookup()
        print(f"  Alias lookup ready: {len(alias_lookup)} entries")

        print(f"\nDetected {len(vendor_sheets)} vendor sheet(s): {', '.join(vendor_sheets)}")
        print("-" * 60)

        for sheet_name in vendor_sheets:
            try:
                import_vendor_products(suppliers_file, sheet_name, alias_lookup=alias_lookup)
            except Exception as e:
                print(f"  Error importing sheet '{sheet_name}': {e}")
                import traceback
                traceback.print_exc()

        print("-" * 60)
        print("\nIMPORT COMPLETE!\n")
        print(f"Total species:  {Species.query.count()}")
        print(f"Total aliases:  {SpeciesAlias.query.count()}")
        print(f"Total vendors:  {Vendor.query.count()}")
        print(f"Total products: {Product.query.count()}")
        print("\nYou can now run the website with: python3 app.py")
        print("="*60 + "\n")


if __name__ == '__main__':
    run_import()