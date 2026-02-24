# Luthia — System Architecture Overview

*Where Tone Begins · luthia.app*

Version 2.0 · February 2026

---

## 1. Purpose & Audience

Luthia is a Flask-based web application built to help luthiers (guitar and instrument builders) compare tonewood prices across European suppliers, explore a species reference database, plan instrument builds, and calculate fret positions. The app is a personal tool developed by a luthier-programmer, serving both as a practical daily-use utility and as a structured learning project for modern web development.

This document describes how Luthia is built and how its components work together. It is written for anyone — technical or otherwise — who wants to understand the system without reading the source code.

---

## 2. The Big Picture

Luthia is a classic server-rendered web application with a thin JavaScript layer on top. The server is written in Python using the Flask micro-framework. Data is stored in a local SQLite database. Users interact with the app through a browser, and the server responds either with complete HTML pages or small JSON data packets (used to update parts of a page without a full reload).

The overall data flow is:

1. The user opens a browser and loads a page (e.g. `/browse`).
2. Flask renders an HTML page using Jinja2 templates, pulling data from the SQLite database via SQLAlchemy (the ORM layer that translates Python objects to database rows and back).
3. JavaScript in the browser listens for user actions (typing in a search box, clicking a filter) and calls JSON APIs (e.g. `/api/products`) to fetch updated data without reloading the whole page.
4. The browser renders the new data dynamically.

---

## 3. Technology Stack

| Layer | Technology | Role |
|---|---|---|
| Web framework | Flask 3.x (Python) | Handles HTTP routing, request/response lifecycle, template rendering |
| ORM / DB layer | Flask-SQLAlchemy + SQLAlchemy | Maps Python model classes to SQLite tables; handles all database queries |
| Database | SQLite (`luthia-data/luthia.db`) | Single-file relational database storing all products, species, builds, and metadata |
| Templating | Jinja2 | Server-side HTML generation with template inheritance and reusable macros |
| Configuration | python-dotenv + config.py | Environment-based config with `DevelopmentConfig` / `TestingConfig` classes |
| Frontend CSS | Vanilla CSS (custom properties) | Two stylesheet files (dark/light) with CSS variables for five named themes |
| Frontend JS | Vanilla JavaScript | Handles live filtering, API calls, sidebar state, theme switching |
| Data import | Pandas + openpyxl | Reads vendor Excel files and imports products into the database |
| Testing | pytest + Flask test client | Integration tests covering all route modules and helper functions |
| Hosting (dev) | Flask dev server, localhost:5000 | Local development only; production deployment not yet configured |

---

## 4. Directory Layout

The repository separates runnable application code from persistent data files, keeping the two independent so that re-deploying the app never risks overwriting uploaded images or the live database.

| Path | Contents |
|---|---|
| `luthia-app/` | All runnable application code |
| `app.py` | Entry point — application factory and server startup |
| `config.py` | Environment-based configuration classes (`BaseConfig`, `DevelopmentConfig`, `TestingConfig`) |
| `models.py` | All SQLAlchemy database model definitions |
| `helpers.py` | Shared pure-Python utilities: `paginate()`, `api_error()`, `get_or_create()`, formatting functions, constants |
| `scripts/` | CLI tools for data management and one-off operations |
| `scripts/import_data.py` | Imports vendor Excel files into the database |
| `scripts/fret_calc_excel.py` | Generates a static fret placement reference Excel workbook |
| `scripts/migrate_images.py` | One-off migration: creates the product_images table |
| `scripts/seed_templates.py` | Seeds instrument templates and dimensional variants |
| `routes/` | Flask Blueprint modules — one file per feature area |
| `templates/` | Jinja2 HTML templates — base layout, one per route, plus `errors/404.html` and `errors/500.html` |
| `static/` | CSS files, JavaScript files, logo |
| `tests/` | pytest test suite with shared fixtures in `conftest.py` |
| `luthia-data/` | Persistent data outside the application directory |
| `luthia-data/luthia.db` | The live SQLite database file |
| `luthia-data/product-images/` | Uploaded product photos (survives app redeployment) |
| `data-sources/` | Excel files containing vendor catalogs and species reference data |
| `documents/` | Design docs, schema diagrams, implementation guides |
| `.env.example` | Template showing required environment variables (`SECRET_KEY`, `APP_ENV`, `UPLOAD_FOLDER`) |

---

## 5. Configuration & Environment

Configuration is managed through `config.py` using a class hierarchy loaded at startup via the `APP_ENV` environment variable. `python-dotenv` loads a `.env` file automatically when the dev server starts.

```
BaseConfig          — shared defaults (SECRET_KEY, UPLOAD_FOLDER, SQLALCHEMY settings)
├── DevelopmentConfig  — DEBUG=True, uses luthia-data/luthia.db
└── TestingConfig      — TESTING=True, uses :memory: SQLite (for test isolation)
```

The application factory (`create_app()`) accepts an optional `test_config` dict that overrides the class-based config, preserving full backward compatibility with the test suite.

Key environment variables:

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Flask session signing | `dev-only-insecure-key` |
| `APP_ENV` | Selects config class | `development` |
| `UPLOAD_FOLDER` | Path for uploaded product images | `~/luthia-data/images` |

---

## 6. Database Schema

All data is stored in a single SQLite file (`luthia-data/luthia.db`). The schema is managed entirely through SQLAlchemy model definitions in `models.py` — no raw SQL schema files exist. When the app starts for the first time, it automatically creates all tables.

### 6.1 Product Catalogue Tables

| Table | Primary Key | Description |
|---|---|---|
| `species` | `species_id` | One row per wood species. Stores scientific name (unique), commercial names in English/Swedish/Portuguese, geographic origin, and a CITES conservation flag. |
| `species_aliases` | `alias_id` | Every alternate name for a species (vendor-specific names, regional names). Used during import to map non-standard names to the canonical species record, and to power the search index. |
| `vendors` | `vendor_id` | European tonewood suppliers. Stores name, country, currency, website, and an active flag (soft-delete). |
| `products` | `product_id` | Central fact table. Each row is one item from a vendor catalog — linking to species, vendor, category, grade, format, and unit. Stores price, dimensions, stock status, a URL, and a `last_updated` timestamp. Indexed on `species_id`, `vendor_id`, `category_id`, and `price`. |
| `categories` | `category_id` | Lookup: Body Blank, Neck Blank, Fretboard Blank, Top Blank, Carpentry Lumber, Finished Fretboard. |
| `grades` | `grade_id` | Lookup: wood quality grades (e.g. AAA, AA, A). Includes a `sort_order` for consistent display. |
| `formats` | `format_id` | Lookup: product formats (e.g. Set, Matched Pair, Single). |
| `units` | `unit_id` | Lookup: pricing units (per piece, per set, per kg, per m). |
| `product_images` | `image_id` | Product photos — either an uploaded file stored in `luthia-data/product-images/` or an external URL. Supports multiple images per product with sort ordering and captions. |

### 6.2 Build Planner Tables

| Table | Primary Key | Description |
|---|---|---|
| `instrument_templates` | `template_id` | Named instrument designs (e.g. Jazz Bass, Precision Bass). Holds the instrument type and identity only. |
| `template_variants` | `variant_id` | A specific configuration of a template: string count, scale length, construction type (bolt-on or neck-through), and all reference blank dimensions in mm. The `has_top` flag determines whether a decorative top is required. |
| `builds` | `build_id` | A saved luthier project. Links a user-chosen name to a template variant, and caches the total price of all selected parts. |
| `build_parts` | `part_id` | One part slot within a build (body, neck, fretboard, top). Stores the assigned product and two computed warning flags: `thickness_warning` (body + top combined thickness exceeds 45 mm) and `dims_unverified` (product has no dimension data on record). |

---

## 7. Application Modules

The application is structured using Flask's Blueprint pattern, where each feature area lives in its own Python module inside the `routes/` folder. Blueprints are independent — they do not import each other — and are assembled into the full application in `app.py`.

### 7.1 `app.py` — Application Factory

`app.py` contains a single `create_app()` function that assembles the complete Flask application. This factory pattern means the app can be instantiated multiple times with different configurations — in particular, the test suite creates it with an in-memory SQLite database so that tests never touch the live data.

The factory: loads configuration from `config.py` via `APP_ENV`, registers 404 and 500 error handlers that render proper Jinja2 error templates, registers all Blueprint modules, adds a custom Jinja2 template filter (`vendor_flag`, which converts country names to emoji flags), and ensures the database schema and the image upload folder exist on first run.

### 7.2 `models.py` — Data Models

All database table definitions live here as SQLAlchemy model classes. The ORM handles all SQL generation — the application code works entirely with Python objects. Relationships between tables are declared using SQLAlchemy's `relationship()` mechanism. The `Product` table includes four explicit indexes (`species_id`, `vendor_id`, `category_id`, `price`) for query performance.

### 7.3 `helpers.py` — Shared Utilities

A module with shared constants and utility functions used across route modules. Contains:

- **Constants**: `CATEGORY_CLASSES`, `VENDOR_FLAGS`, `ROLE_CATEGORIES`, `THICKNESS_WARN_LIMIT`, `ALLOWED_EXTENSIONS`
- **`paginate(query, page, per_page)`**: shared pagination helper returning `{items, total, page, pages, per_page}`
- **`api_error(message, status=400)`**: normalised JSON error response `{ok: false, errors: [...]}`
- **`get_or_create(model, **kwargs)`**: returns an existing ORM row or inserts and flushes a new one
- **`staleness_info(last_updated)`**: returns a date string and colour hex for price freshness display
- **`fmt_dims(product)`**: formats T × W × L dimensions as a human-readable string
- **`fmt_image(img)`**: serialises a `ProductImage` ORM object to a JSON-ready dict; uploaded images are served from `/uploads/<filename>`
- **`allowed_file(filename)`**: validates image upload extensions

### 7.4 `routes/` — Feature Blueprints

| Blueprint | URL prefix(es) | What it does |
|---|---|---|
| `browse.py` | `/browse`, `/api/products` | Renders the main product catalogue page. Products are fetched asynchronously via `/api/products`, which supports filtering, sorting, and pagination (50 rows/page). Uses the shared `paginate()` helper. |
| `species.py` | `/species`, `/api/species` | Renders the species reference guide. Full-text search across all name languages and aliases, CITES filter, in-stock filter. Uses the shared `paginate()` helper (48 rows/page). |
| `builds.py` | `/builds`, `/api/builds` | Powers the build planner. Build creation redirects correctly via `redirect(url_for(...))`. Part updates use `datetime.now(timezone.utc)` (non-deprecated). |
| `fret.py` | `/fret`, `/api/fret` | Fret position calculator using the equal temperament formula. Exports a formatted `.xlsx` file via `/api/fret/export`. |
| `vendors.py` | `/vendors`, `/api/vendors` | Vendor management page. Full CRUD API: list, create, update, and soft-delete/restore (toggles the `active` flag). |
| `templates.py` | `/templates` | Instrument template management — creating and editing instrument designs and their dimensional variants. |
| `images.py` | `/api/products/<id>/images`, `/api/images/<id>`, `/uploads/<filename>` | Image management API. Upload, URL attachment, deletion, caption editing. Serves uploaded files from `luthia-data/product-images/` via `send_from_directory()`. Error responses use the shared `api_error()` helper. |

---

## 8. Error Handling

Flask error handlers are registered in `app.py` for HTTP 404 and 500 errors. Both render proper Jinja2 templates (`templates/errors/404.html` and `templates/errors/500.html`) that extend `base.html` and display user-friendly messages inside the full app layout. No stack traces are ever exposed to the browser.

All JSON API endpoints return errors in a consistent envelope: `{"ok": false, "errors": ["message"]}` with an appropriate HTTP status code (400 for validation errors, 404 for not found, 500 for server errors). The `api_error()` helper in `helpers.py` centralises this construction.

---

## 9. Frontend Architecture

The frontend is deliberately minimal — no JavaScript framework, no build step, no bundler. All CSS and JavaScript are plain files served directly from the `static/` folder.

### 9.1 CSS Theme System

Two CSS files provide all styling: `luthia-dark.css` and `luthia-light.css`. Both files are loaded on every page. The active mode and theme are determined by data attributes on the `<html>` element (`data-mode`, `data-theme`), which CSS custom properties then respond to. Theme switching is instant — the browser re-evaluates the CSS variables with no round-trip to the server.

Five named themes are available — Beeswax, Amber (default), Maple, Mahogany, and Spruce — each named after a material or wood species relevant to lutherie. The selected theme and mode are persisted in `localStorage`.

### 9.2 JavaScript

Two JavaScript files handle all client-side behaviour:

- **`sidebar.js`** — manages sidebar expand/collapse state, theme switcher swatches, and the light/dark mode toggle. All state persisted in `localStorage`.
- **`luthia-app.js`** — handles browse and species page logic: debounced search inputs, filter dropdowns, API calls via `fetch()`, table rendering from JSON, column sorting, pagination, product detail panel, and inline edit forms.

The build planner pages use JavaScript embedded in their templates for the variant dropdown cascade and the part-assignment candidate picker.

### 9.3 Template System

All HTML is generated by Jinja2 on the server. The layout follows a base template (`base.html`) that defines the full page chrome — sidebar, header, breadcrumb, theme scripts — and a content block that each page template fills in. Reusable component markup is extracted into Jinja2 macros in `templates/macros/`. Error pages live in `templates/errors/`.

---

## 10. Data Import Pipeline

The product database is populated manually by running `import_data.py` from the command line. The pipeline works as follows:

1. The luthier maintains Excel workbooks in `data-sources/`. Each vendor has its own sheet within a suppliers workbook. A separate species workbook provides the canonical species reference.
2. Running `python scripts/import_data.py` from `luthia-app/` presents an interactive menu to select the target Excel files. Pass `--dry-run` to show the diff report only without touching the database.
3. Before importing, the tool runs a **diff report**: it compares the Excel data against the current database and prints a summary of new products, removed products, price changes, and stock changes — grouped by vendor.
4. After confirmation, it imports in this order: (1) reference data, (2) species and aliases, (3) products from each vendor sheet.
5. Each vendor import is **wrapped in a database transaction**. If an import fails midway, `db.session.rollback()` restores the database to its pre-import state and the script continues with the next vendor sheet.
6. Species names are resolved through an alias lookup table. If a vendor uses an unrecognised name, a new species record is created automatically.

---

## 11. Image Storage & Serving

Uploaded product images are stored in `luthia-data/product-images/` — outside the application source directory — so they survive app redeployment or re-cloning. Images are served by a dedicated route in `images.py` using Flask's `send_from_directory()`, and referenced in the frontend as `/uploads/<filename>`. The upload folder path is configurable via the `UPLOAD_FOLDER` environment variable.

---

## 12. Testing Strategy

The test suite lives in `luthia-app/tests/` and is run with pytest. The architecture is designed for testability:

- The application factory pattern means tests instantiate the app with an in-memory SQLite database, completely isolated from `luthia.db`.
- `conftest.py` provides shared fixtures: `app` (session-scoped), `db_session` (drops and recreates schema per test), `client` (Flask test client), and `seed_db` (inserts a minimal realistic dataset).
- Integration tests cover all seven route modules and helper functions:

| Test file | Coverage |
|---|---|
| `test_browse.py` | Product catalogue API — filtering, sorting, pagination, inline edit |
| `test_builds.py` | Build planner — creation, part assignment, candidate lookup, deletion |
| `test_fret.py` | Fret calculator — pure function correctness, API validation, xlsx export |
| `test_species.py` | Species API — search, CITES filter, pagination, detail endpoint |
| `test_vendors.py` | Vendor CRUD — create, duplicate validation, update, soft-delete toggle |
| `test_helpers.py` | `staleness_info`, `fmt_dims`, and other formatting utilities in isolation |
| `test_images.py` | Image upload, URL attachment, deletion, caption editing |

---

## 13. Request / Response Flow

The following walkthrough traces a typical user interaction — browsing products by species — from browser to database and back.

| Step | What happens |
|---|---|
| 1 | User navigates to `/browse` in the browser. |
| 2 | Flask routes the request to `browse_bp.browse()`. The function queries the database for distinct species, vendors, and categories (with product counts) to populate the filter dropdowns. These are passed as raw ORM objects; Jinja2 renders the `<option>` elements with auto-escaping. |
| 3 | Flask renders `index.html` (extending `base.html`) with the dropdown data and basic page stats. The HTML response is sent to the browser. |
| 4 | The browser renders the page shell. JavaScript calls `/api/products?page=1` immediately after load. |
| 5 | Flask routes the API call to `browse_bp.api_products()`. It reads query parameters, constructs a SQLAlchemy query, paginates it using the shared `paginate()` helper (50 rows), and serialises the results to JSON. |
| 6 | JavaScript receives the JSON and renders the product table rows into the DOM. |
| 7 | User types in the species filter box. JavaScript debounces 300 ms and calls `/api/products?species_id=42&page=1`. |
| 8 | The server re-runs the filtered query and returns updated JSON. JavaScript clears the table and renders the new rows. |
| 9 | User clicks a product row. JavaScript calls `/api/products/123` (detail endpoint) and renders a side panel with full product and species information. |

---

## 14. Key Design Decisions

| Decision | Rationale |
|---|---|
| Blueprint-based architecture | Decomposed from a single 1,098-line `app.py` into focused modules. Each Blueprint owns its routes and business logic, making the codebase navigable and testable. |
| SQLite as the database | Appropriate for a single-user local tool. No server process, no setup, and the entire database is a single file. |
| Excel as the source of truth | Vendor catalogs are naturally managed in spreadsheets. The import pipeline reads Excel directly, so the luthier works in a familiar tool. |
| Environment-based configuration | `config.py` with `DevelopmentConfig` / `TestingConfig` classes loaded via `APP_ENV`. `python-dotenv` loads `.env` automatically. Secrets never hardcoded. |
| No JavaScript framework | Avoids build toolchain complexity. Vanilla JS with the Fetch API covers all interaction needs. |
| CSS custom properties for themes | Five themes switchable at runtime without a server round-trip, with no flash of unstyled content because the theme is restored from `localStorage` in a `<head>` script block. |
| Application factory pattern | Enables clean test isolation — each test run gets a fresh app with an in-memory database, no shared global state. |
| Shared helper functions | `paginate()`, `api_error()`, and `get_or_create()` in `helpers.py` eliminate duplication across route modules and ensure consistent API response shapes. |
| Soft-delete for vendors | The `active` flag is toggled rather than deleting vendor rows, which preserves the full product history and allows re-activation. |
| Transaction safety for imports | Each vendor import is wrapped in a `try/except` with `db.session.rollback()`, protecting the database from partial imports on failure. |
| Image storage outside app directory | `luthia-data/product-images/` is decoupled from the application source so uploaded files survive redeployment. |
| Flask error handlers | 404 and 500 handlers registered in `app.py` render proper Jinja2 error pages. No stack traces exposed to the browser. |

---

## 15. Database Inventory (as of Feb 2026)

| Metric | Count |
|---|---|
| Total products | 969 |
| Active vendors | 4 |
| Wood species | 103 |
| Supplier countries covered | 4 (Sweden, Portugal, Italy, Spain) |

---

*Luthia · luthia.app · Where tone begins · Architecture v2.0 · February 2026*
