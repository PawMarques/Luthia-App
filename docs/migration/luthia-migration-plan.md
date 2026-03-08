# Luthia — Migration Project Plan
### Flask + Jinja2 → Flask API + React TypeScript SPA

*Project Manager Reference Document · March 2026*

---

## Executive Summary

This document outlines the full plan for migrating Luthia from a server-rendered Flask + Jinja2 application to a modern two-tier architecture: a Flask API backend and a React TypeScript frontend powered by shadcn/ui components.

The migration preserves the entire Flask backend, all Python data import scripts, the SQLite database, and all existing API endpoints. The effort is focused exclusively on replacing the Jinja2 view layer with a React frontend. The Python import scripts are relocated to `data-sources/scripts/` as part of the repository restructure.

**Primary goal:** Access the shadcn/ui component ecosystem for a modern, consistent, and maintainable UI while retaining the stability and capability of the existing Flask backend.

---

## Final Repository Structure

```
luthia/                          # Repository root
├── luthia-server/               # Flask — API server (renamed from luthia-app)
│   ├── app.py
│   ├── config.py
│   ├── models.py
│   ├── helpers.py
│   ├── routes/
│   ├── static/                  # Legacy — removed at end of migration
│   ├── templates/               # Legacy — removed at end of migration
│   └── tests/
├── luthia-client/               # React + TypeScript — UI (new)
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── lib/
│   │   │   ├── api.ts
│   │   │   └── types.ts
│   │   └── main.tsx
│   ├── vite.config.ts
│   └── package.json
├── luthia-data/                 # SQLite + product images (unchanged)
│   ├── luthia.db
│   └── product-images/
└── data-sources/                # All data-related assets
    ├── scripts/                 # Python import + utility scripts (relocated)
    │   ├── import_data.py
    │   ├── fret_calc_excel.py
    │   ├── migrate_images.py
    │   └── seed_templates.py
    ├── vendors/                 # Vendor Excel catalogs
    └── species/                 # Species reference workbook
```

---

## Cross-Platform Development Notes

The project is developed primarily on macOS with occasional work on a Windows machine.

- **Windows machine:** Use WSL2 (Windows Subsystem for Linux) to ensure consistent behaviour with macOS and the eventual Linux hosting environment. VS Code connects to WSL2 via the Remote - WSL extension.
- **Synchronisation:** Git + GitHub is the synchronisation layer between machines. Never leave uncommitted work when switching machines.
- **Database:** `luthia-data/` is excluded from Git. `luthia.db` is maintained on the primary macOS machine. Copy manually to the Windows machine when needed. Treat the Windows machine as a development/testing environment.
- **Runtime pinning:** Pin Python version via `.python-version` (pyenv) and Node via `.nvmrc` to ensure identical environments on both machines.

---

## Technology Decisions

| Concern | Choice | Rationale |
|---|---|---|
| Frontend framework | React + TypeScript | Required for shadcn/ui (Radix UI dependency) |
| Bundler | Vite | Fast, minimal config, first-class React/TS support |
| Component library | shadcn/ui | Primary migration goal |
| Styling | Tailwind CSS | shadcn/ui dependency; utility-first |
| Routing | React Router v7 | Simple config-based routing; Flask stays dumb |
| Data fetching | TanStack Query | Caching, loading states, pagination — essential for Luthia's data-heavy pages |
| Forms | React Hook Form + Zod | shadcn's recommended pairing; Zod schemas validate API responses |
| HTTP client | Native fetch + typed wrapper | Sufficient at Luthia's scale |
| Backend | Flask (unchanged) | Pure API server; all business logic retained |
| Database | SQLite (unchanged) | No changes required |
| Import scripts | Python (relocated, unchanged) | Python + Pandas is the right tool; no reason to change |

---

## Phased Plan

---

### Phase 0 — Repository Restructure & API Hardening

**Goal:** Prepare the Flask codebase to function as a standalone API server before any React code is written. All changes are in Python. Nothing is broken or removed.

**Milestone:** Flask runs cleanly from `luthia-server/`, all API endpoints are stable and complete, CORS is configured, environment is documented.

**Estimated duration:** 1 week

---

#### Task 0.1 — Rename and restructure the repository

- Rename `luthia-app/` to `luthia-server/`
- Create `luthia-client/` as an empty placeholder directory
- Move `luthia-app/scripts/` to `data-sources/scripts/`
- Organise `data-sources/` into `vendors/` and `species/` subdirectories
- Verify `luthia-data/` and `data-sources/` remain at the repository root (not nested inside `luthia-server/`)
- Commit the restructure as a single isolated commit before any other changes

*Claude Code usage: ask Claude Code to verify no import paths or file references are broken after the rename.*

---

#### Task 0.2 — Fix script paths

- Audit all scripts in `data-sources/scripts/` for hardcoded paths that referenced the old `luthia-app/scripts/` location
- Update relative paths to reflect the new location relative to the repository root
- Test each script runs correctly from its new location
- Update the README with the new script paths and usage instructions

---

#### Task 0.3 — Add API versioning prefix

- In `luthia-server/app.py`, update all Blueprint registrations to mount under `/api/v1/`
- Example: `app.register_blueprint(browse_bp, url_prefix='/api/v1')`
- Update any frontend JavaScript that calls `/api/products` to call `/api/v1/products`
- Run the existing pytest suite to confirm nothing is broken

*Claude Code usage: ask Claude Code to update all Blueprint registrations and find any hardcoded API paths in the existing JS files.*

---

#### Task 0.4 — Audit and complete API response shapes

For each API endpoint, verify it returns everything a React component would need without a second request. Specific checks:

- **Products API** (`/api/v1/products`): confirm species name, vendor name, category name, grade name, format name, and unit name are included in each product row — not just their IDs
- **Species API** (`/api/v1/species`): confirm aliases are included in detail responses
- **Builds API** (`/api/v1/builds`): confirm part detail responses include full product and species info
- **All list endpoints**: confirm pagination metadata (`total`, `page`, `pages`, `per_page`) is present
- **All write endpoints** (POST/PATCH/DELETE): confirm they return the updated object, not just a success flag

*Claude Code usage: ask Claude Code to audit each route file and list any endpoints that return only IDs where names are also needed.*

---

#### Task 0.5 — Standardise error responses

- Verify every route uses the `api_error()` helper for all error cases
- Check that HTTP status codes are semantically correct (400 for validation, 404 for not found, 409 for conflicts, 500 for server errors)
- Add any missing error handling for edge cases found during the audit

---

#### Task 0.6 — Install and configure Flask-CORS

```bash
pip install flask-cors
```

- Configure CORS in `app.py` to allow requests from `http://localhost:5173` (Vite's default dev port)
- Restrict allowed origins to development only; production will be same-domain and won't need CORS
- Update `requirements.txt`

---

#### Task 0.7 — Add environment and runtime pins

- Add `.python-version` file (pyenv) specifying the Python version in use
- Add `.nvmrc` file specifying the Node version to use (even though Node isn't used yet — sets it up for Phase 1)
- Add `.gitattributes` for consistent line endings across macOS and Windows/WSL2
- Ensure `luthia-data/` is in `.gitignore`
- Ensure `.env` is in `.gitignore` (verify, don't assume)

---

#### Task 0.8 — Verify test suite passes

- Run `pytest` from `luthia-server/` and confirm all tests pass after the restructure
- Fix any broken test paths or imports caused by the directory rename

---

### Phase 1 — Frontend Scaffolding & Theme System

**Goal:** A running React + TypeScript project with shadcn/ui installed, the Amber dark theme pixel-perfect, and the full five-theme system working. No feature pages yet — just the foundation.

**Milestone:** `npm run dev` starts the Luthia UI shell at localhost:5173 with correct branding, themes, and dark/light mode. API calls proxied to Flask work.

**Estimated duration:** 1 week

---

#### Task 1.1 — Initialise the React project

```bash
npm create vite@latest luthia-client -- --template react-ts
cd luthia-client
npm install
```

Install core dependencies:

```bash
npm install react-router-dom @tanstack/react-query react-hook-form zod
npm install -D tailwindcss @tailwindcss/vite
```

Initialise shadcn:

```bash
npx shadcn@latest init
```

During shadcn init: select the Amber base colour, dark mode via CSS class.

*Claude Code usage: ask Claude Code to scaffold the initial project structure and install all dependencies.*

---

#### Task 1.2 — Configure Vite API proxy

In `vite.config.ts`, add the proxy so API calls to `/api/v1/*` are forwarded to the Flask server during development:

```typescript
server: {
  proxy: {
    '/api': 'http://localhost:5000'
  }
}
```

This eliminates CORS issues in development and means the React app never hardcodes the API base URL.

---

#### Task 1.3 — Port the theme system

- Translate the five CSS custom property themes (Beeswax, Amber, Maple, Mahogany, Spruce) from `luthia-dark.css` / `luthia-light.css` into Tailwind's CSS variable layer
- shadcn uses CSS variables internally — the two systems compose naturally
- Implement dark/light mode via a class on the `<html>` element (matching the current behaviour)
- Persist selected theme and mode to `localStorage`
- Use the Amber dark theme as the reference — get it pixel-perfect before the others

*Claude Code usage: ask Claude Code to extract the CSS custom properties from the existing stylesheet and convert them to Tailwind CSS variable definitions.*

---

#### Task 1.4 — Build the typed API client

Create `src/lib/api.ts` and `src/lib/types.ts`:

- Define TypeScript types for all data models: `Product`, `Species`, `Vendor`, `Build`, `BuildPart`, `Category`, `Grade`, `Format`, `Unit`
- Define `PaginatedResponse<T>` generic type
- Define `ApiError` type matching Flask's `{"ok": false, "errors": [...]}` envelope
- Write a base `fetchApi()` wrapper handling errors consistently
- Write typed fetch functions for each endpoint group (`getProducts()`, `getSpecies()`, etc.)

*Claude Code usage: ask Claude Code to generate the TypeScript types from the Flask models.py and route response shapes.*

---

#### Task 1.5 — Configure TanStack Query

- Wrap the app in `QueryClientProvider` in `main.tsx`
- Configure sensible defaults: `staleTime`, `retry` behaviour
- Write the first query hooks: `useProducts()`, `useVendors()` — these will be used in Phase 2 to verify the proxy works end-to-end

---

#### Task 1.6 — Build the app shell

Components to build in order:

1. **`AppLayout`** — outer wrapper: sidebar + main content area
2. **`Sidebar`** — navigation links (Browse, Species, Builds, Fret, Vendors), brand mark, collapse state persisted to localStorage. Use shadcn `Sheet` component for mobile drawer behaviour
3. **`ThemeSwitcher`** — five colour swatches + dark/light toggle, wired to the theme system from Task 1.3
4. **`Breadcrumb`** — use shadcn's built-in Breadcrumb component
5. **`PageHeader`** — consistent page title + subtitle pattern used across all pages

---

#### Task 1.7 — Configure React Router

Set up routes in `src/main.tsx` or a dedicated `src/router.tsx`:

```
/            → redirect to /browse
/browse      → BrowsePage (placeholder)
/species     → SpeciesPage (placeholder)
/builds      → BuildsPage (placeholder)
/fret        → FretPage (placeholder)
/vendors     → VendorsPage (placeholder)
```

Create empty placeholder page components for each route so navigation works before content is built.

---

### Phase 2 — Vendors Page

**Goal:** First fully functional feature page. Establishes the data table pattern, CRUD operation pattern, and form pattern that all subsequent pages will reuse.

**Milestone:** Vendors page is feature-complete and visually matches the Luthia brand. The Jinja2 vendors template is deleted.

**Estimated duration:** 3–4 days

---

#### Task 2.1 — Build the Vendors data table

- Use shadcn `Table` component
- Columns: name, country, currency, website, status (active/inactive)
- Use the `useVendors()` TanStack Query hook
- Add the country emoji flag (port the `vendor_flag` Jinja2 filter as a TypeScript utility function)
- Loading and empty states

---

#### Task 2.2 — Build the Add Vendor form

- Use shadcn `Dialog` + `Form` (React Hook Form + Zod)
- Define Zod schema matching the Flask POST /api/v1/vendors validation
- Fields: name, country, currency, website
- Submit calls Flask API, invalidates the TanStack Query cache on success (table refreshes automatically)
- Error handling: display Flask validation errors inline

---

#### Task 2.3 — Build inline edit and soft-delete

- Edit: shadcn `Dialog` pre-populated with existing vendor data
- Soft-delete toggle: shadcn `Switch` or button that calls the active toggle endpoint
- Confirm deletion with shadcn `AlertDialog`

---

#### Task 2.4 — Delete Jinja2 vendors template

- Remove `templates/vendors.html` from `luthia-server/`
- Remove the HTML-rendering route from `vendors.py` (keep all API routes)
- Confirm Flask returns 404 for `/vendors` (React Router now owns that path)

---

### Phase 3 — Species Page

**Goal:** Read-heavy page with search, filtering, and pagination. Establishes the filter pattern reused on the Browse page.

**Milestone:** Species page is feature-complete. Jinja2 species template deleted.

**Estimated duration:** 4–5 days

---

#### Task 3.1 — Build the Species data table

- shadcn `Table` with columns: commercial name, scientific name, origin, CITES status, in-stock indicator
- Pagination controls (shadcn `Pagination`)
- Loading and empty states

---

#### Task 3.2 — Build the filter bar

- Debounced search input (300ms, matching existing behaviour) — use shadcn `Input`
- CITES filter dropdown — shadcn `Select`
- In-stock toggle — shadcn `Switch`
- Filters update TanStack Query params, which refetches automatically

---

#### Task 3.3 — Build the Species detail panel

- shadcn `Sheet` (side panel) triggered on row click
- Display: all name variants (English, Swedish, Portuguese, scientific), origin, aliases, CITES status, products in stock
- Matches the detail panel behaviour in the existing JS

---

#### Task 3.4 — Delete Jinja2 species template

---

### Phase 4 — Browse Page

**Goal:** The core page. More complex filtering, more columns, product detail panel, inline edit. Reuses filter patterns from Phase 3.

**Milestone:** Browse page is feature-complete. Jinja2 browse template deleted.

**Estimated duration:** 5–7 days

---

#### Task 4.1 — Build the Products data table

- shadcn `Table` with columns: species, vendor, category, grade, format, dimensions, price, currency, stock status, last updated (with staleness colour indicator)
- Port the `staleness_info()` logic as a TypeScript utility
- Port the `fmt_dims()` logic as a TypeScript utility
- 50 rows per page, pagination controls

---

#### Task 4.2 — Build the filter bar

Reuse the filter pattern from Phase 3:

- Search input (debounced)
- Species dropdown (searchable — use shadcn `Combobox`)
- Vendor dropdown
- Category dropdown
- Grade dropdown
- In-stock toggle
- Sort controls (column header clicks)

---

#### Task 4.3 — Build the Product detail panel

- shadcn `Sheet` triggered on row click
- Full product details: all fields, species info, vendor info, product images
- Image gallery using `product_images` data

---

#### Task 4.4 — Build the inline edit form

- Accessible via the detail panel
- Fields: price, currency, stock status, dimensions, product URL
- Zod validation, Flask API PATCH call, cache invalidation on success

---

#### Task 4.5 — Delete Jinja2 browse template

---

### Phase 5 — Fret Calculator Page

**Goal:** Self-contained calculator page. No pagination complexity. Establishes the form-output pattern.

**Milestone:** Fret calculator is feature-complete with xlsx export working. Jinja2 fret template deleted.

**Estimated duration:** 2–3 days

---

#### Task 5.1 — Build the calculator form

- shadcn `Form` with React Hook Form + Zod
- Fields: scale length, number of frets, tuning reference
- Submits to Flask `/api/v1/fret` and displays results

---

#### Task 5.2 — Build the results display

- Table of fret positions with distance from nut and distance from previous fret
- Visual fretboard diagram (optional enhancement)

---

#### Task 5.3 — Wire up the xlsx export

- Export button triggers `window.location.href = '/api/v1/fret/export?...'` with current form values as query params
- Flask returns the xlsx file as a download — no React-side file handling needed

---

#### Task 5.4 — Delete Jinja2 fret template

---

### Phase 6 — Build Planner

**Goal:** Most complex page. Multi-step state, variant cascade, part assignment with candidate picker, warning flags.

**Milestone:** Build Planner is feature-complete. Jinja2 build templates deleted.

**Estimated duration:** 7–10 days

---

#### Task 6.1 — Build the Builds list page

- shadcn `Card` grid of saved builds
- Each card: build name, instrument type, variant, total price, warning badge if any parts have issues
- New build button

---

#### Task 6.2 — Build the New Build form

- shadcn `Dialog`
- Step 1: name + instrument template selection (shadcn `Select`)
- Step 2: variant selection — cascade updates based on template choice
- Creates build via Flask API, redirects to build detail

---

#### Task 6.3 — Build the Build detail page

- Part slots displayed as cards: Body, Neck, Fretboard, Top (conditional on `has_top`)
- Each slot shows: assigned product (if any), price, dimensions, warning flags
- Thickness warning and unverified dimensions warning — port the logic from the Flask route

---

#### Task 6.4 — Build the part assignment candidate picker

- shadcn `Dialog` with a searchable, filterable product list
- Filtered to the appropriate category for each part slot
- Sorted by price
- Selecting a product calls the Flask PATCH endpoint and updates the build

---

#### Task 6.5 — Build delete confirmation

- shadcn `AlertDialog` for build deletion
- Confirm before calling Flask DELETE endpoint

---

#### Task 6.6 — Delete all Jinja2 build templates

---

### Phase 7 — Decommission Jinja2 & Production Build

**Goal:** Flask stops serving HTML entirely. React owns all routing. Production serving is configured.

**Milestone:** The app runs cleanly in production mode. Jinja2 is fully removed. The architecture matches the target design.

**Estimated duration:** 3–4 days

---

#### Task 7.1 — Remove all Jinja2 HTML rendering from Flask routes

- For each Blueprint, remove the `render_template()` calls and their associated route functions
- Keep all API routes intact
- Remove the Jinja2 `vendor_flag` filter registration from `app.py`

---

#### Task 7.2 — Remove templates and legacy static files

- Delete `luthia-server/templates/` entirely
- Delete `luthia-server/static/` (CSS, JS files are now in `luthia-client/`)
- Remove Jinja2 from `requirements.txt` if it is listed explicitly (Flask bundles it, so it may not be)

---

#### Task 7.3 — Add Flask catch-all route for production

Flask needs to serve the React app's `index.html` for any non-API path, so that React Router can handle client-side navigation:

```python
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    if path.startswith('api/'):
        return api_error('Not found', 404)
    return send_from_directory(app.config['REACT_BUILD_DIR'], 'index.html')
```

Add `REACT_BUILD_DIR` (pointing to `luthia-client/dist/`) to `config.py`.

---

#### Task 7.4 — Configure Vite production build

- Run `npm run build` in `luthia-client/` — outputs to `luthia-client/dist/`
- Verify all assets are fingerprinted correctly
- Verify the React app loads correctly when served by Flask

---

#### Task 7.5 — Update all documentation

- Update `README.md` to reflect the new structure, setup instructions, and dev workflow
- Update `luthia-architecture-overview.md` to v3.0
- Document the two-process dev workflow (`flask run` + `vite dev`)
- Document the production build process

---

#### Task 7.6 — Final test pass

- Run `pytest` — all backend tests should still pass (Flask logic is unchanged)
- Manual smoke test of every page and every write operation
- Test on both macOS and Windows/WSL2

---

## Timeline Summary

| Phase | Description | Duration | Cumulative |
|---|---|---|---|
| Phase 0 | Repository restructure & API hardening | 1 week | Week 1 |
| Phase 1 | Frontend scaffolding & theme system | 1 week | Week 2 |
| Phase 2 | Vendors page | 4 days | Week 3 |
| Phase 3 | Species page | 5 days | Week 4–5 |
| Phase 4 | Browse page | 7 days | Week 6–7 |
| Phase 5 | Fret calculator | 3 days | Week 8 |
| Phase 6 | Build planner | 10 days | Week 9–11 |
| Phase 7 | Decommission & production build | 4 days | Week 12 |

**Total estimated duration: 10–12 weeks** at a comfortable part-time pace.

The Browse page (Phase 4) and Build Planner (Phase 6) are the critical path. Everything else can be adjusted without affecting the overall timeline significantly.

---

## Risk Register

---

### Risk 1 — API response shapes are incomplete
**Probability:** High · **Impact:** Medium

The current API was built to supplement Jinja2 templates that had server-side context available. Some endpoints may return only foreign key IDs where the React frontend needs resolved names (e.g. `species_id: 42` instead of `species_name: "Sitka Spruce"`).

**Mitigation:**
- Task 0.4 specifically audits every endpoint before React development begins
- Fix all response shapes in Phase 0 so the frontend is never blocked by missing data
- Define TypeScript types (Task 1.4) before building any pages — type mismatches surface immediately at compile time

---

### Risk 2 — Theme system translation loses visual fidelity
**Probability:** Medium · **Impact:** Medium

The current CSS custom property system is carefully crafted. Translating it into Tailwind's variable layer may produce subtle colour or spacing differences, particularly around the five named themes and the dark/light mode interaction.

**Mitigation:**
- Treat Phase 1 Task 1.3 as a design task, not just a code task — open the current app and the new app side by side
- Get the Amber dark theme pixel-perfect before any other work proceeds — this is the reference
- Keep the original CSS files in the repository until Phase 7 as a reference source
- Ask Claude Code to do a direct variable-by-variable translation rather than reinterpretation

---

### Risk 3 — TanStack Query cache invalidation causes stale UI
**Probability:** Medium · **Impact:** Low

If query cache keys are not structured correctly, write operations (add vendor, update product, assign build part) may not trigger the correct refetch, leaving the UI showing stale data.

**Mitigation:**
- Establish a clear query key convention in Phase 1 before any pages are built (e.g. `['products', filters]`, `['vendors']`)
- Document the convention so it is applied consistently across all pages
- Test every write operation during the page it is introduced — don't defer testing to Phase 7

---

### Risk 4 — Build Planner state complexity underestimated
**Probability:** Medium · **Impact:** High

The Build Planner has more interdependent state than any other page: template → variant cascade, per-slot part assignment, conditional top slot, two warning flags per part. This is the most likely page to require significant rework.

**Mitigation:**
- Phase 6 is scheduled last, when React patterns are well established from four previous pages
- Spend time in Phase 0 auditing the Build Planner Flask routes specifically — understand all the state transitions before writing any React
- Break the implementation into the smallest possible tasks (as structured above) and test each one before proceeding
- Consider building a simplified version first (list + create + basic part assignment) before adding warning logic

---

### Risk 5 — Database divergence between macOS and Windows machines
**Probability:** Medium · **Impact:** Low

Working across two machines with local SQLite databases means data state can diverge. A product added or import run on one machine won't appear on the other.

**Mitigation:**
- Establish a clear primary machine policy: macOS is the primary, Windows is for development and testing only
- Keep a copy of `luthia.db` in a non-Git location (e.g. a shared folder or cloud drive) for manual sync when needed
- The import scripts in `data-sources/scripts/` are the authoritative way to rebuild the database from source Excel files — document this as the recovery procedure if machines get out of sync

---

### Risk 6 — Flask route removal breaks something unexpected
**Probability:** Low · **Impact:** High

Phase 7 removes all Jinja2 rendering from Flask. If any route had side effects beyond rendering (e.g. session handling, redirect logic) that were not replicated in the API layer during the migration, removing it could break functionality silently.

**Mitigation:**
- During each page migration phase (2–6), remove the corresponding Jinja2 template immediately after the React page is verified working — don't leave it to Phase 7
- This surfaces any issues page-by-page rather than as a batch in the final phase
- The existing pytest suite covers all route modules and will catch regressions in the API layer
- Keep Git commits granular so any removal can be reverted cleanly

---

### Risk 7 — Vite proxy configuration issues in development
**Probability:** Low · **Impact:** Medium

Misconfigured Vite proxy can cause API calls to fail silently or return unexpected responses during development, making it difficult to distinguish frontend bugs from proxy bugs.

**Mitigation:**
- Configure and verify the Vite proxy as the very first step in Phase 1 (Task 1.2), before building any UI
- Test the proxy with a direct `fetch('/api/v1/vendors')` call in the browser console before writing any components
- Add explicit proxy logging in `vite.config.ts` during development

---

### Risk 8 — shadcn/ui component API changes
**Probability:** Low · **Impact:** Low

shadcn/ui is under active development. The component API may change between the time this plan is written and the time individual phases are executed, requiring adjustments to component usage.

**Mitigation:**
- Pin the shadcn/ui version in `package.json` at the start of Phase 1 and do not update it during the migration
- Perform a single, deliberate update pass after Phase 7 is complete if desired
- shadcn components are copied into your own codebase (not imported from npm), so you own the code — changes in upstream shadcn don't automatically affect your project

---

## Working with Claude Code

Each phase and task in this plan is designed to be executed collaboratively with Claude Code. Suggested usage patterns:

- **Auditing tasks** (Phase 0): paste the relevant Flask route file and ask Claude Code to identify gaps in response shapes or missing error handling
- **Type generation** (Phase 1): paste `models.py` and ask Claude Code to generate the equivalent TypeScript types
- **Component scaffolding** (Phases 2–6): describe the component requirements and ask Claude Code to generate the initial implementation using shadcn/ui primitives
- **Refactoring** (Phase 7): paste each Blueprint file and ask Claude Code to identify and remove the HTML-rendering routes while preserving the API routes
- **Test writing**: after each page, ask Claude Code to generate integration tests for the new React components

Keep Claude Code sessions focused on one task at a time. Provide the relevant source files as context rather than describing them from memory.

---

*Luthia · luthia.app · Where tone begins · Migration Plan v1.0 · March 2026*
