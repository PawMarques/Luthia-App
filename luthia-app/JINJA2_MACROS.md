# Jinja2 Macros Refactor

Date: 2026-02-23
Scope: `luthia-app/`

---

## Problem

Several Python functions in `routes/builds.py` and `routes/templates.py` were generating
raw HTML strings instead of delegating rendering to Jinja2. This mixed presentation and
logic, made the HTML hard to read and maintain, and bypassed Jinja2's auto-escaping
(XSS risk via `| safe` on database-originated values).

---

## Files Created

### `templates/macros/builds.html`

Jinja2 macros for the Build Planner domain.

| Macro | Replaces | Description |
|---|---|---|
| `build_card(build, parts_done, parts_total, progress_pct)` | `_build_card_html()` | Summary card on `/builds` index |
| `part_row_assigned(part, product, role_icon)` | `_assigned_part_html()` | Part row with a product assigned |
| `part_row_empty(part, role_icon)` | `_empty_part_html()` | Part row with no product selected |

### `templates/macros/instrument_templates.html`

Jinja2 macros for the Instrument Template domain.

| Macro | Replaces | Description |
|---|---|---|
| `template_card(t)` | `_template_card_html()` | Summary card on `/templates` index |
| `variant_summary(v)` | `_variant_summary_html()` | Read-only dimension summary inside a card |
| `variant_edit(v)` | `_variant_edit_html()` | Full dimension edit form block |

---

## Files Modified

### `routes/builds.py`

**Functions removed** (were generating raw HTML):

- `_build_card_html(b)`
- `_render_parts(build)`
- `_assigned_part_html(part)`
- `_empty_part_html(part)`

**Route handler changes:**

| Handler | Before | After |
|---|---|---|
| `builds_index()` | Passed `cards_html` (HTML string) | Passes `builds` queryset directly |
| `builds_detail()` | Passed `parts_html` (HTML string) and called `_render_parts()` | Passes `build.parts` and `role_icons` dict; total computed as plain `float` |
| `builds_detail()` | Passed `case_warn` (HTML string with `<span>` tags) | Removed; case-warning logic moved to template |
| `builds_new()` | Passed `tpl_opts` (HTML `<option>` string) | Passes `templates` list |

---

### `routes/templates.py`

**Functions removed** (were generating raw HTML):

- `_template_card_html(t)`
- `_variant_summary_html(v)`
- `_variant_edit_html(v)`

**Route handler changes:**

| Handler | Before | After |
|---|---|---|
| `templates_index()` | Passed `cards_html` (HTML string) | Passes `templates` list directly |
| `templates_edit()` | Passed `variants_html` (HTML string) | Passes `variants` (sorted list) |
| `templates_edit()` | Passed `error_html` (HTML string) | Passes `errors` (plain list of strings) |

---

### HTML Templates

| Template | Change |
|---|---|
| `templates/builds/index.html` | `{{ cards_html \| safe }}` → `{% for b in builds %}` loop calling `build_card` macro |
| `templates/builds/detail.html` | `{{ parts_html \| safe }}` → `{% for part in build.parts %}` loop calling `part_row_assigned` / `part_row_empty` macros |
| `templates/builds/detail.html` | `{{ case_warn \| safe }}` → inline `{% if ref.overall_length_mm > 1250 %}` / `{% if ref.body_width_mm > 380 %}` conditionals |
| `templates/builds/new.html` | `{{ tpl_opts \| safe }}` → `{% for t in templates %}` loop |
| `templates/templates/index.html` | `{{ cards_html \| safe }}` → `{% for t in templates %}` loop calling `template_card` macro |
| `templates/templates/edit.html` | `{{ variants_html \| safe }}` → `{% for v in variants %}` loop calling `variant_edit` macro |
| `templates/templates/edit.html` | `{{ error_html \| safe }}` → `{% if errors %}` block with escaped `{{ e }}` |

---

## Security

All `| safe` usages on database-originated or user-supplied values have been removed from
every template touched in this refactor. The only remaining `| safe` calls in the project
are in `templates/index.html` (the Browse page — outside this refactor's scope).

Jinja2 auto-escaping is now active for all values rendered through the new macros, which
prevents XSS via malicious content stored in the database (e.g. a product name or build
name containing `<script>` tags).

---

## Architecture

```
Before
──────
routes/builds.py      — business logic + HTML string generation interleaved
routes/templates.py   — form handling + HTML string generation interleaved
templates/builds/     — renders pre-built HTML strings with | safe
templates/templates/  — renders pre-built HTML strings with | safe


After
─────
routes/builds.py      — business logic only; passes ORM objects to templates
routes/templates.py   — form handling only; passes ORM objects to templates
templates/macros/
  builds.html                 — all build-domain HTML in one place
  instrument_templates.html   — all template-domain HTML in one place
templates/builds/             — imports macros; no | safe on DB data
templates/templates/          — imports macros; no | safe on DB data
```

---

## Test Results

```
67 passed, 25 warnings in 0.25s
```

All pre-existing tests pass without modification.
