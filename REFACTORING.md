# Luthia — Refactoring Summary

Date: 2026-02-23
Scope: `tonewood-app/`

---

## Goals

- Improve readability, maintainability, and performance
- Rename all `tonewood` identifiers in filenames and references to `luthia`
- Apply SOLID principles to the codebase architecture
- Add comments for non-obvious logic
- Maintain identical external behaviour and the same tech stack (Flask · SQLAlchemy · SQLite · Vanilla JS · Jinja2)

---

## File Renames

| Before | After |
|---|---|
| `static/tonewood-dark.css` | `static/luthia-dark.css` |
| `static/tonewood-app.js` | `static/luthia-app.js` |
| `tonewood.db` | `luthia.db` |

---

## New Files Created

### `helpers.py`
Shared constants and pure utility functions extracted from `app.py`.

**Rationale (SRP):** No Flask or SQLAlchemy imports — the module can be imported and unit-tested in complete isolation from the web framework.

| Symbol | Purpose |
|---|---|
| `CATEGORY_CLASSES` | Maps category names to CSS badge class names |
| `VENDOR_FLAGS` | Maps vendor country names to emoji flags |
| `THICKNESS_WARN_LIMIT` | Max combined body+top thickness before a planing warning (45 mm) |
| `ROLE_CATEGORIES` | Maps build part role names to product category names |
| `ALLOWED_EXTENSIONS` | Accepted image upload file extensions |
| `allowed_file()` | Validates an upload filename against the allowed extension set |
| `staleness_color()` | Returns a hex colour based on data age in months |
| `staleness_info()` | Returns `(date_string, colour_hex)` for a `last_updated` datetime |
| `fmt_dims()` | Formats T × W × L dimensions from a Product as a human-readable string |
| `fmt_image()` | Serialises a `ProductImage` ORM object to a JSON-safe dict |

---

### `routes/__init__.py`
Package marker for the new `routes/` sub-package.

---

### `routes/browse.py`
Browse page and product catalogue API (Blueprint: `browse`).

**Routes:**

| Method | Path | Handler |
|---|---|---|
| `GET` | `/browse` | `browse()` |
| `GET` | `/api/products` | `api_products()` |
| `GET` | `/api/products/<id>` | `api_product_detail()` |
| `PUT` | `/api/products/<id>` | `api_product_edit()` |

**Private helpers extracted from route handlers:**

| Function | Purpose |
|---|---|
| `_build_product_query()` | Applies filter parameters to the Product query |
| `_apply_sort()` | Adds an ORDER BY clause based on the requested column |
| `_formats_for_category()` | Returns Format options for the dynamic category dropdown |
| `_product_row()` | Serialises a Product to a table-row dict |
| `_get_or_create_format()` | Finds or creates a Format row by name |
| `_get_or_create_grade()` | Finds or creates a Grade row by name |

---

### `routes/builds.py`
Build planner routes and business logic (Blueprint: `builds`).

**Routes:**

| Method | Path | Handler |
|---|---|---|
| `GET` | `/builds` | `builds_index()` |
| `GET / POST` | `/builds/new` | `builds_new()` |
| `GET` | `/builds/<id>` | `builds_detail()` |
| `GET` | `/api/builds/<id>/candidates/<role>` | `api_build_candidates()` |
| `PATCH` | `/api/builds/<id>/parts/<part_id>` | `api_build_part_update()` |
| `DELETE` | `/api/builds/<id>` | `api_build_delete()` |

**Business logic helpers:**

| Function | Purpose |
|---|---|
| `_roles_for_variant()` | Returns ordered part roles for a variant (body, neck, fretboard, ±top) |
| `_candidate_products()` | Tier-1/2 product matching for a build part role |
| `_minimum_dims_for_role()` | Extracted from `_candidate_products` — computes required blank minimums per role |
| `_check_thickness_warning()` | Sets/clears the body+top thickness warning flag |

**HTML rendering helpers** (keep rendering concerns out of route handlers):

| Function | Purpose |
|---|---|
| `_build_card_html()` | Renders a build summary card for the index page |
| `_render_parts()` | Renders all part rows for a build detail page |
| `_assigned_part_html()` | Renders a part row that has a product assigned |
| `_empty_part_html()` | Renders an empty part slot row |

---

### `routes/templates.py`
Instrument template management routes (Blueprint: `templates`).

**Routes:**

| Method | Path | Handler |
|---|---|---|
| `GET` | `/templates` | `templates_index()` |
| `GET / POST` | `/templates/<id>/edit` | `templates_edit()` |

**Private helpers:**

| Function | Purpose |
|---|---|
| `_save_template()` | Validates and persists template form data |
| `_save_variant_fields()` | Reads variant dimension fields from POST and updates in-place |
| `_template_card_html()` | Renders a summary card for one template |
| `_variant_summary_html()` | Renders the read-only dimension summary for a variant |
| `_variant_edit_html()` | Renders the edit form block for a variant |

---

### `routes/images.py`
Image management API (Blueprint: `images`).

**Routes:**

| Method | Path | Handler |
|---|---|---|
| `POST` | `/api/products/<id>/images` | `api_image_upload()` |
| `DELETE` | `/api/images/<id>` | `api_image_delete()` |
| `PATCH` | `/api/images/<id>/caption` | `api_image_caption()` |

**Private helpers:**

| Function | Purpose |
|---|---|
| `_save_url_image()` | Persists an external URL image record |
| `_save_file_image()` | Validates and persists an uploaded file image |
| `_next_sort_order()` | Returns `max(sort_order) + 1` for a product's images |

---

## Modified Files

| File | Change |
|---|---|
| `app.py` | Reduced from 1 098 lines to 55. Now a lean application factory (`create_app()`) that configures Flask, registers blueprints, and ensures the DB exists. `UPLOAD_FOLDER` moved to Flask config. Startup message updated to "Luthia". |
| `templates/base.html` | CSS `href` updated to `luthia-dark.css`. `localStorage` key updated to `luthia-sidebar`. |
| `templates/index.html` | Script `src` updated to `luthia-app.js`. |
| `static/sidebar.js` | `STORAGE_KEY` updated to `'luthia-sidebar'`. |
| `static/builds.css` | Comments updated to reference `luthia-dark.css`. |
| `import_data.py` | Database URI updated to `luthia.db`. |
| `seed_templates.py` | Database URI updated to `luthia.db`. |
| `migrate_images.py` | Database URI updated to `luthia.db`. |

---

## SOLID Principles Applied

### Single Responsibility (SRP)
Each module now owns exactly one concern:

| Module | Responsibility |
|---|---|
| `models.py` | Data layer — ORM models and schema |
| `helpers.py` | Pure formatting utilities and constants |
| `routes/browse.py` | Product browsing and catalogue API |
| `routes/builds.py` | Build planner logic and API |
| `routes/templates.py` | Template management |
| `routes/images.py` | Image upload and management |
| `app.py` | Application assembly and startup |

### Open/Closed (OCP)
New feature areas (e.g. fret calculator, species guide) can be added as new blueprints without modifying any existing module.

### Dependency Inversion (DIP)
Route modules depend on the `models` abstraction and `helpers` interface, not on each other. `helpers.py` has zero framework dependencies, making it the most stable layer.

---

## Architecture Before and After

```
Before
──────
app.py  (1 098 lines — routes, helpers, constants, business logic all mixed)


After
─────
app.py          (55 lines  — application factory only)
helpers.py      (95 lines  — shared constants + formatting utilities)
routes/
  __init__.py   (2  lines  — package marker)
  browse.py     (190 lines — browse page + products API)
  builds.py     (310 lines — build planner routes + business logic)
  templates.py  (260 lines — template management routes)
  images.py     (110 lines — image CRUD API)
```
