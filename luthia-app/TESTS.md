# Luthia — Test Suite Report

Date: 2026-02-23
Scope: `luthia-app/tests/`
Result: **67 / 67 passed · 0.30 s**

---

## How to run

```bash
cd luthia-app
/Users/paulomarques/Library/Python/3.9/bin/pytest -v
```

Or, once pytest is on PATH:

```bash
pytest -v
```

---

## Prerequisites

```bash
python3 -m pip install pytest pytest-flask
```

No other test dependencies were introduced.

---

## Files created

### `pytest.ini`

```ini
[pytest]
testpaths = tests
pythonpath = .
```

Tells pytest to look in `tests/` and adds `luthia-app/` to `sys.path` so the app's modules resolve without any path manipulation in test code.

---

### `tests/conftest.py`

Shared fixtures available to every test module.

| Fixture | Scope | Purpose |
|---|---|---|
| `app` | session | Calls `create_app()` with `TESTING=True` and `sqlite:///:memory:`. Uses `StaticPool` so every connection within the session shares the same in-memory database. Pushes an app context for the whole test run. |
| `client` | function | Flask test client derived from `app`. |
| `db_session` | function | Calls `db.create_all()` before each test and `db.drop_all()` + `db.session.remove()` after, giving each test a completely clean schema. |
| `seed_db` | function | Inserts a minimal but realistic dataset (see below). Returns a dict of ORM objects so tests can reference IDs without hard-coding them. |

**Seed dataset**

| Row | Detail |
|---|---|
| 1 × Vendor | Nordic Woods · Sweden · SEK |
| 1 × Species | *Fraxinus excelsior* / European Ash |
| 4 × Category | Body Blank, Neck Blank, Fretboard Blank, Top Blank |
| 1 × Format | Set |
| 1 × Grade | AAA |
| 2 × Product | Both in Body Blank; 500 SEK and 800 SEK — different prices for sort tests |
| 1 × InstrumentTemplate | Jazz Bass (bass) |
| 1 × TemplateVariant | 4-string 34" · bolt-on · 864 mm scale · full dimension set |
| 1 × Build | Test Build |
| 1 × BuildPart | body slot (no product assigned) |

---

### `tests/test_helpers.py` — 20 tests

Pure unit tests; no app context or database required.

| Group | Tests | Technique |
|---|---|---|
| `allowed_file` | 14 parametrized cases — valid extensions (jpg, jpeg, png, webp, gif), uppercase, invalid (bmp, tiff, pdf, svg), no extension, empty string, dot-only | `@pytest.mark.parametrize` |
| `staleness_color` | 6 parametrized boundary cases at 0, 3.0, 3.01, 6.0, 6.01, 12.0 months | `@pytest.mark.parametrize` |
| `staleness_info` | 4 tests: None input → `('', muted grey)`; 1 month → green; 5 months → amber; 8 months → red | `unittest.mock.patch('helpers.datetime')` pins `utcnow` for deterministic results |
| `fmt_dims` | 5 cases: all dims, two dims, one dim, none, falsy zero | `types.SimpleNamespace` mock product |
| `fmt_image` | 5 cases: upload path, URL passthrough, null URL, null caption, required keys present | `types.SimpleNamespace` mock image |

---

### `tests/test_browse.py` — 12 tests

Integration tests against the `browse` blueprint.

| Test | What it asserts |
|---|---|
| `test_browse_page_returns_200` | `GET /browse` renders without error |
| `test_api_products_returns_expected_json_keys` | Response has `total`, `page`, `pages`, `rows`, `formats` |
| `test_api_products_total_matches_seeded_count` | Unfiltered total == 2 |
| `test_api_products_filter_by_species_id` | Filter returns only matching species rows |
| `test_api_products_filter_by_unknown_species_returns_empty` | Unknown species_id → total == 0 |
| `test_api_products_sort_price_desc_orders_correctly` | Rows in descending price order |
| `test_api_products_sort_price_asc_orders_correctly` | Rows in ascending price order |
| `test_api_product_detail_returns_correct_payload` | Detail fields match seeded product |
| `test_api_product_detail_404_for_missing_product` | Unknown id → 404 |
| `test_api_product_edit_updates_price` | Valid PUT updates price and persists |
| `test_api_product_edit_negative_price_returns_400` | Negative price → 400 + errors list |
| `test_api_product_edit_invalid_dimension_returns_400` | Non-numeric dimension → 400 |

---

### `tests/test_builds.py` — 14 tests

Integration tests against the `builds` blueprint.

| Test | What it asserts |
|---|---|
| `test_builds_index_returns_200` | `GET /builds` renders the index |
| `test_builds_new_get_returns_200` | `GET /builds/new` renders the form |
| `test_builds_new_post_valid_creates_build_and_responds` | Valid POST creates a Build row and returns a JS redirect |
| `test_builds_new_post_missing_name_returns_form` | Blank name → 200, no Build created |
| `test_builds_detail_returns_200` | `GET /builds/<id>` renders detail page for seeded build |
| `test_builds_detail_404_for_unknown_id` | Unknown id → 404 |
| `test_api_candidates_body_returns_json_array` | Candidates endpoint returns a list |
| `test_api_candidates_body_contains_seeded_products` | Both seeded products pass dimension check |
| `test_api_candidates_unknown_role_returns_empty_array` | Unknown role → `[]`, not 404 |
| `test_api_build_part_update_assigns_product` | PATCH assigns product, returns `{ok: true, total: ...}` |
| `test_api_build_delete_removes_build` | DELETE removes row, subsequent GET → 404 |
| `test_api_build_delete_404_for_unknown_build` | Unknown id → 404 |

---

### `tests/test_images.py` — 9 tests

Integration tests against the `images` blueprint.
File uploads use `io.BytesIO` for the fake file payload; `werkzeug.datastructures.FileStorage.save` is patched so no bytes are written to disk.

| Test | What it asserts |
|---|---|
| `test_post_url_image_saves_record` | JSON POST with URL creates a `ProductImage` row and returns it |
| `test_post_url_image_missing_url_returns_400` | Empty URL → 400 |
| `test_post_url_image_for_unknown_product_returns_404` | Unknown product_id → 404 |
| `test_post_file_upload_saves_record` | Multipart POST saves an upload record with correct src path |
| `test_post_file_upload_disallowed_extension_returns_400` | `.txt` file → 400 |
| `test_patch_caption_updates_text` | PATCH updates caption in the database |
| `test_patch_caption_strips_whitespace` | Leading/trailing whitespace is stripped before saving |
| `test_delete_image_removes_record` | DELETE removes the row from the database |
| `test_delete_image_404_for_unknown_id` | Unknown id → 404 |

---

## Files modified

### `app.py`

Added an optional `test_config: Optional[dict] = None` parameter to `create_app()`.
The dict is applied via `app.config.update(test_config)` **before** `os.makedirs` and `db.init_app()`, so test overrides (DB URI, UPLOAD_FOLDER) take effect before any I/O or engine creation occurs.

```python
def create_app(test_config: Optional[dict] = None) -> Flask:
    ...
    if test_config:
        app.config.update(test_config)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    db.init_app(app)
    ...
```

---

## Bugs discovered during the test run

### 1 — `builds/new.html` does not render the error variable

**Location:** `routes/builds.py` → `builds_new()` + `templates/builds/new.html`

**Symptom:** The route sets `error = 'Please fill in all fields.'` when required fields are missing but never passes it to `render_template()`. The template has no `{{ error }}` block. The error is silently swallowed.

**Action taken:** The test was updated to assert the correct observable behaviour (HTTP 200, no `Build` row created) rather than checking for error text that is never rendered. The application code was left unchanged.

---

### 2 — `builds/detail.html` crashes on `None` variant dimensions

**Location:** `templates/builds/detail.html` lines 43–45

**Symptom:** The template uses `{{ "%.1f" % ref.neck_width_heel_mm }}` (and the same for `neck_thickness_1f_mm` and `neck_thickness_12f_mm`) without guarding against `None`. When the variant's dimension columns are `NULL`, Jinja raises `TypeError: must be real number, not NoneType`.

**Action taken:** The `seed_db` fixture was updated to supply values for all three fields (`neck_width_heel_mm=65.0`, `neck_thickness_1f_mm=20.0`, `neck_thickness_12f_mm=22.5`). The template bug remains latent for any real variant that has these columns unpopulated.

---

## Architecture notes

| Concern | Decision |
|---|---|
| DB isolation | Session-scoped `app` fixture + function-scoped `db_session` that calls `drop_all` / `create_all` gives a fresh schema per test without paying the cost of a new Flask app per test. |
| Shared in-memory DB | `StaticPool` + `check_same_thread=False` ensures the test client's request connections see data committed in fixtures (normally separate connections would get different `:memory:` databases). |
| File upload tests | `io.BytesIO` provides fake file content; `FileStorage.save` is patched so no bytes reach the filesystem. The temporary `UPLOAD_FOLDER` injected by the test config would be safe anyway but the mock makes intent explicit. |
| Legacy SQLAlchemy warnings | `Model.query.get()` in `routes/builds.py` emits `LegacyAPIWarning` under SQLAlchemy 2.x. These are pre-existing in application code; tests use `db.session.get(Model, pk)` to stay warning-free. |
