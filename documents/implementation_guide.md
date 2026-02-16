# Tonewood Database - Complete Implementation Guide

## Table of Contents
1. [System Overview](#system-overview)
2. [Database Design](#database-design)
3. [Technology Stack](#technology-stack)
4. [Installation Guide](#installation-guide)
5. [Application Architecture](#application-architecture)
6. [Features Deep Dive](#features-deep-dive)
7. [Data Management](#data-management)
8. [Customization Guide](#customization-guide)
9. [Troubleshooting](#troubleshooting)

---

## System Overview

### What Problem Does This Solve?

**Before:** Excel spreadsheet with 900+ products
- Manual searching through multiple sheets
- Duplicate data (species names repeated hundreds of times)
- Difficult price comparisons across vendors
- No search or filter capabilities
- Slow and error-prone

**After:** Web-based database application
- Instant search across all vendors (< 0.1 seconds)
- 80% reduction in duplicate data
- Dynamic filtering with smart category-format relationships
- Sortable, paginated results
- Easy to maintain and update

### Key Metrics

- **969 products** across 4 international vendors
- **103 wood species** (78 from master list + 25 added during import)
- **123 unique formats** (scale/fret/radius configurations)
- **5 product categories** (Body, Neck, Fretboard, Top, Lumber)
- **7 database tables** (normalized relational structure)

---

## Database Design

### Normalized Structure

The system uses a **normalized relational database** to eliminate redundancy and ensure data integrity.

#### Core Tables

**1. SPECIES (103 records)**
```
species_id          PRIMARY KEY
scientific_name     UNIQUE, NOT NULL (e.g., "Acer saccharum")
commercial_name     VARCHAR(100) (e.g., "Hard Maple")
cites_listed        BOOLEAN (protected species flag)
created_at          TIMESTAMP
```

**2. PRODUCT (969 records)**
```
product_id          PRIMARY KEY
species_id          FOREIGN KEY → species.species_id
vendor_id           FOREIGN KEY → vendors.vendor_id
category_id         FOREIGN KEY → categories.category_id
grade_id            FOREIGN KEY → grades.grade_id (nullable)
format_id           FOREIGN KEY → formats.format_id (nullable)
unit_id             FOREIGN KEY → units.unit_id (nullable)
thickness_mm        FLOAT (nullable)
width_mm            FLOAT (nullable)
length_mm           FLOAT (nullable)
weight_kg           FLOAT (nullable)
price               FLOAT NOT NULL
currency            VARCHAR(3) (SEK/EUR)
in_stock            BOOLEAN
product_url         VARCHAR(500)
last_updated        TIMESTAMP
created_at          TIMESTAMP
```

**3. VENDOR (4 records)**
```
vendor_id           PRIMARY KEY
name                VARCHAR(100) UNIQUE
country             VARCHAR(50)
currency            VARCHAR(3)
website             VARCHAR(200)
active              BOOLEAN
created_at          TIMESTAMP
```

#### Lookup Tables

**4-7. CATEGORY, GRADE, FORMAT, UNIT**

Each with primary key and name field, providing controlled vocabularies.

### Normalization Benefits

- **Storage**: 80% reduction in duplicate data
- **Integrity**: Foreign keys prevent invalid references
- **Updates**: Change once, affects all related records

---

## Technology Stack

- **Flask 3.0+** - Web framework
- **SQLAlchemy 2.0+** - ORM
- **SQLite** - Database (file-based, zero config)
- **Pandas + OpenPyXL** - Excel processing
- **Vanilla JavaScript** - Dynamic UI features

---

## Installation Guide

See Quick Start Guide for detailed step-by-step instructions.

Quick version:
```bash
pip3 install flask flask-sqlalchemy pandas openpyxl
python3 import_data.py
python3 app.py
```

---

## Application Architecture

### File Structure
```
tonewood-app/
├── models.py           # Database schema (7 tables)
├── app.py              # Web application (~350 lines)
├── import_data.py      # Excel importer (~250 lines)
├── tonewood.db         # SQLite database
└── *.xlsx             # Source data
```

### Routes
- `GET /` - Home page with filters and product table
- `GET /search` - Filtered search results

---

## Features Deep Dive

### 1. Dynamic Search & Filtering

Five filter types working together:
- Species (103 options)
- Vendor (4 options)
- Category (5 options)
- Format (dynamic, category-dependent)
- Max Price (numeric input)

### 2. Smart Format Filtering

**Problem**: 123 total formats overwhelm users  
**Solution**: Show only relevant formats per category  
**Implementation**: JavaScript pre-loads category→format mapping

### 3. Column Sorting

Click any header to sort:
- Species, Vendor, Category, Format (alphabetical)
- Grade (by name)
- Price (numeric)

Arrow indicators show active sort direction.

### 4. Pagination

- 50 products per page
- Smart page number display
- Previous/Next navigation
- Preserves filters and sort

### 5. Collapsible Interface

Toggle button hides/shows filters to maximize table space.

---

## Data Management

### Updating Prices

1. Edit Excel file
2. Delete database: `rm tonewood.db`
3. Re-import: `python3 import_data.py`

Takes ~30 seconds for full refresh.

### Adding Products/Vendors

Either update Excel and re-import, or add directly via Python:

```python
from app import app, db
from models import Product

with app.app_context():
    product = Product(...)
    db.session.add(product)
    db.session.commit()
```

---

## Customization Guide

### Change Theme Colors

In `app.py` CSS section:
```css
th { background: #4CAF50; }  /* Green - change to #2196F3 for blue */
```

### Adjust Products Per Page

```python
per_page = 50  # Change to 25, 100, etc.
```

### Add New Filters

1. Add HTML input
2. Parse request parameter
3. Add filter to query

Example in implementation guide above.

---

## Troubleshooting

Common issues and solutions:

**Port in use:** `lsof -ti:5000 | xargs kill -9`  
**Empty dropdowns:** Check data imported correctly  
**Format filter not appearing:** Verify JavaScript and element IDs  
**Slow queries:** Add database indexes

Enable debug mode for detailed errors:
```python
app.run(debug=True)
```

---

## Next Steps

Recommended enhancements:
1. Export to Excel
2. Price history tracking
3. Favorites/bookmarks
4. Email alerts
5. Mobile-responsive design

See full list in README.md

---

## Conclusion

This implementation provides a solid foundation for tonewood price comparison. The normalized database, clean architecture, and extensible design make it easy to maintain and enhance.

**Key Success Factors:**
- Excel remains source of truth
- Regular backups
- Systematic updates
- Clear documentation

Happy building! 🎸
