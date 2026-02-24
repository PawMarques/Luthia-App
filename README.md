# Luthia — Where Tone Begins

> A web application for luthiers to compare European tonewood prices, explore wood species, and plan instrument builds.

**Domain:** [luthia.app](https://luthia.app) · **Version:** 2.0 · **Status:** Active development

---

## What It Does

Luthia is a personal tool built by a luthier-programmer. It solves a real problem in instrument building: tonewood prices vary significantly across European suppliers, and comparing them manually is tedious. The app brings that data together in one place, alongside tools that support the full build planning workflow.

**Core features:**

- **Browse & Compare** — Search and filter 969 products across 4 vendors by species, category, grade, and price. Live filtering with no page reloads.
- **Species Reference** — A database of 103 wood species with scientific names, commercial names in English, Swedish, and Portuguese, geographic origin, and CITES conservation status.
- **Build Planner** — Save instrument projects, assign tonewoods to each part slot (body, neck, fretboard, top), and get automatic warnings for thickness conflicts or missing dimensions.
- **Fret Calculator** — Equal temperament fret position calculator with `.xlsx` export.
- **Vendor Management** — Track supplier details, currencies, and active status. Soft-delete preserves product history.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python / Flask 3.x |
| Database | SQLite via SQLAlchemy ORM |
| Templates | Jinja2 (server-rendered HTML) |
| Frontend | Vanilla JS + CSS custom properties |
| Data import | Pandas + openpyxl (Excel → SQLite) |
| Testing | pytest + Flask test client |

No JavaScript framework. No build step. Deliberately minimal on the frontend — the complexity lives in the data and the domain logic.

---

## Project Structure

```
luthia-app/          # All application code
├── app.py           # Application factory (create_app)
├── config.py        # DevelopmentConfig / TestingConfig
├── models.py        # SQLAlchemy models
├── helpers.py       # Shared utilities (paginate, api_error, staleness_info…)
├── scripts/         # CLI tools for data management and one-off operations
│   ├── import_data.py        # Imports vendor Excel files into the database
│   ├── fret_calc_excel.py    # Generates a static fret placement reference workbook
│   ├── migrate_images.py     # One-off migration: creates the product_images table
│   └── seed_templates.py     # Seeds instrument templates and dimensional variants
├── routes/          # Flask Blueprints — one file per feature
│   ├── browse.py    # Product catalogue + /api/products
│   ├── species.py   # Species guide + /api/species
│   ├── builds.py    # Build planner + /api/builds
│   ├── fret.py      # Fret calculator + /api/fret
│   ├── vendors.py   # Vendor CRUD + /api/vendors
│   ├── templates.py # Instrument template management
│   └── images.py    # Image upload + /uploads/<filename>
├── templates/       # Jinja2 HTML templates
├── static/          # CSS and JS files
└── tests/           # pytest suite

luthia-data/         # Persistent data — survives redeployment
├── luthia.db        # Live SQLite database
└── product-images/  # Uploaded product photos

data-sources/        # Excel vendor catalogs (source of truth)
documents/           # Architecture docs, schema diagrams
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- pip

### Setup

```bash
# Clone and install dependencies
git clone <repo-url>
cd luthia-app
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — set SECRET_KEY, APP_ENV, UPLOAD_FOLDER

# Run the development server
flask run
```

The app will be available at `http://localhost:5000`. The database and upload folder are created automatically on first run.

### Importing Data

Vendor catalogs are maintained as Excel files in `data-sources/`. To import:

```bash
python scripts/import_data.py
```

The tool shows a diff report (new items, price changes, removals) before writing anything. Use `--dry-run` to preview only. Each vendor import is transactional — a failure rolls back without affecting other vendors.

---

## Running Tests

```bash
pytest
```

Tests use an in-memory SQLite database — the live `luthia.db` is never touched. The suite covers all seven route modules and shared helper functions.

---

## Configuration

Configuration is class-based (`config.py`) and selected via the `APP_ENV` environment variable.

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Flask session signing | `dev-only-insecure-key` |
| `APP_ENV` | `development` or `testing` | `development` |
| `UPLOAD_FOLDER` | Path for uploaded product images | `~/luthia-data/images` |

---

## Database at a Glance

| Metric | Count |
|---|---|
| Products | 969 |
| Active vendors | 4 |
| Wood species | 103 |
| Countries covered | 4 (SE, PT, IT, ES) |

The full schema is documented in `documents/luthia-architecture-overview.md` and the schema diagram at `documents/luthiadatabaseschema.png`.

---

## Design Decisions Worth Knowing

- **Excel as source of truth.** Vendor catalogs live in spreadsheets — the natural format for this data. The import pipeline reads them directly.
- **SQLite.** Single-user local tool. No database server to manage; the entire database is one file.
- **Blueprint architecture.** The app was decomposed from a 1,098-line monolith into focused route modules. Each Blueprint is independently testable.
- **Soft-delete for vendors.** Toggling an `active` flag preserves all product history and allows reactivation.
- **Image storage outside the app directory.** `luthia-data/product-images/` is decoupled from source code so uploads survive redeployment.
- **No JS framework.** Vanilla JS with the Fetch API covers all interaction needs without a build toolchain.

---

## Branding

- **Typefaces:** Cormorant Light Italic (wordmark/tagline) · IBM Plex Sans + IBM Plex Mono (UI)
- **Themes:** Five named themes switchable at runtime — Beeswax, Amber (default), Maple, Mahogany, Spruce
- **Mark:** A cross fleury (cross botonnée), used historically by craft guilds and instrument makers

---

## Roadmap

- [ ] Full pytest coverage across all modules
- [ ] Migrate remaining HTML generation from Python to Jinja2 templates
- [ ] Persistent sidebar navigation (shadcn dashboard pattern)
- [ ] Enhanced species database with tonal characteristics
- [ ] Production deployment configuration

---

*Luthia · luthia.app · Where tone begins*