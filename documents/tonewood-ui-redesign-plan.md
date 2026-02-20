# Tonewood Finder — UI Redesign
## Goals, Constraints, Feasibility & Implementation Plan

**Date:** 2026-02-20  
**Status:** Approved — ready for implementation  
**Chosen variant:** A (Flush sidebar)

---

## 1. Background & Problem Statement

Tonewood Finder is a Flask/SQLite web application for comparing tonewood prices across European suppliers and planning instrument builds. The current UI consists of two isolated page families — the Tonewood Finder (browse/search) and the Build Planner — each with their own headers, nav tabs, and back-link hacks. There is no unified shell.

As features expand (Fret Calculator, Species Guide, Vendor management, etc.), the bolt-on approach breaks down. There is no persistent sense of "where am I in this app", and adding a new section means duplicating the entire page scaffolding again.

---

## 2. Goals

- Replace the fragmented per-page headers with a single persistent left sidebar that serves as the authoritative navigation for the entire application
- Match the collapse-to-icons behaviour of the shadcn sidebar-07 pattern (`collapsible="icon"`)
- Unify the Tonewood Finder and Build Planner under one shell without disrupting existing functionality or routes
- Establish a scalable template architecture (Jinja2 `base.html`) so future features plug in cleanly
- Preserve the existing dark colour palette and visual language (#111113 page, #18181b panels, #34d399 accent)

---

## 3. Constraints

**Technical stack is fixed.** The app is Python Flask + SQLite + vanilla HTML/CSS/JS. No React, no Node build pipeline. The shadcn sidebar is a React component — the collapse behaviour must be re-implemented in vanilla CSS and JS.

**No backend changes.** All Flask routes, API endpoints, database queries, and business logic remain untouched. This is a pure UI/template layer change.

**Backward compatibility.** All existing URLs (`/`, `/builds`, `/builds/<id>`, `/builds/new`, `/templates`, `/templates/<id>/edit`) must continue to work. No redirects, no route renaming.

**Single-user local app.** No authentication, no multi-tenant concerns. `localStorage` is a valid and appropriate mechanism for persisting sidebar state.

**Existing CSS files stay.** `tonewood-dark.css` and `builds.css` are kept. New sidebar shell styles are added to `tonewood-dark.css`; `builds.css` continues to handle build-specific component styles. Duplicated header/nav-tab CSS in both files is removed as part of the migration.

---

## 4. Reference Material

| Source | Used for |
|---|---|
| shadcn sidebar-07 (`app-sidebar.tsx`, `page.tsx`) | Collapse-to-icons behaviour, `SidebarRail`, nav item structure |
| shadcn dashboard-01 (`layout.tsx`, `page.tsx`, `theme.css`) | Inset variant layout, `SiteHeader` + breadcrumb pattern, CSS variable approach |
| shadcn sidebar docs (`ui.shadcn.com/docs/components/base/sidebar`) | `collapsible="icon"` props, width CSS variables, keyboard shortcut |
| Prototype A (`sidebar-flush.html`) | Approved visual design — flush variant chosen |

---

## 5. Feasibility Assessment

**Overall: High ✅**

The shadcn sidebar system is a React state machine layered over CSS custom properties. The underlying mechanics are straightforward to translate into vanilla JS:

- `SidebarProvider` state → `data-sidebar="expanded|collapsed"` attribute on `<body>`
- `--sidebar-width` / `--sidebar-width-icon` CSS variables → standard `:root` custom properties
- `collapsible="icon"` → CSS rules scoped to `[data-sidebar="collapsed"]`
- `SidebarRail` → a thin absolutely-positioned `<div>` with a resize cursor
- `useSidebar()` hook → ~80 lines of vanilla JS
- Cookie-based state persistence (`layout.tsx`) → `localStorage`
- `SidebarTrigger` → a `<button>` in the site header
- Keyboard shortcut (`Ctrl+B`) → `keydown` event listener

The main risk is **Phase 1** — converting all routes from f-string HTML to `render_template()`. It touches every route in `app.py` but involves no logic changes. It must be done in a single session to avoid a mixed state. Each subsequent phase is independently deployable.

---

## 6. Current Route Inventory

All 8 page routes currently return self-contained f-string HTML documents. All must be converted to `render_template()` in Phase 1.

| Route | Function | Current nav context |
|---|---|---|
| `GET /` | `index()` | Tonewood Finder header |
| `GET /products/<id>` | `product_detail()` | Tonewood Finder header |
| `GET /builds` | `builds_index()` | Build Planner header + Builds/Templates tabs |
| `GET/POST /builds/new` | `builds_new()` | Build Planner header |
| `GET /builds/<id>` | `build_detail()` | Build Planner header + Builds/Templates/[Build] tabs |
| `GET /templates` | `templates_index()` | Build Planner header + Builds/Templates tabs |
| `GET/POST /templates/<id>/edit` | `templates_edit()` | Build Planner header |

The JSON API routes (`/api/products`, `/api/builds/...`) are untouched — they return JSON and have no UI layer.

---

## 7. Sidebar Layout

```
┌─────────────────────────────────────────────────────────────┐
│ SIDEBAR (232px expanded / 52px collapsed)                   │
│                                                             │
│  🎸 Tonewood Finder          ← brand header                 │
│     v1.0 · 969 products                                     │
│  ─────────────────────────                                  │
│  MAIN                                                       │
│  🔍  Browse Woods      [969] ← active item example          │
│  🔨  Build Planner                                          │
│  ⊞   Fret Calculator                                        │
│  🌿  Species Guide                                          │
│  ─────────────────────────                                  │
│  MANAGE                                                     │
│  ⊡   Templates                                              │
│  📦  Vendors                                                │
│  ─────────────────────────                                  │
│  [PB] Paulo · Luthier        ← sidebar footer               │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ MAIN AREA                                                   │
│  [☰] | Tonewood Finder › Browse Woods    [Import] [+ Build] │
│  ───────────────────────────────────────────────────────    │
│                                                             │
│  PAGE CONTENT  ({% block content %})                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Collapsed state (52px):** icons only, centred. Labels hidden via `opacity: 0`. Hover over an icon shows a tooltip with the label, positioned to the right of the sidebar rail.

---

## 8. Implementation Plan

### Phase 1 — Jinja2 Template Infrastructure
**Scope:** Create `templates/` directory. Add Jinja2 `render_template` imports to `app.py`. Convert all 7 page routes from f-string returns to `render_template('path/page.html', **context)`.

**New files:**
```
templates/
  base.html                  ← sidebar shell (built in Phase 2)
  index.html                 ← Browse Woods page
  products/detail.html       ← Product detail
  builds/index.html          ← Build list
  builds/new.html            ← New build form
  builds/detail.html         ← Build detail + picker modal
  templates/index.html       ← Template list
  templates/edit.html        ← Template editor
```

**Changes to `app.py`:** Route functions only — swap f-string `return` for `render_template()`. No logic changes. Each route passes an `active_nav` string and `breadcrumb` list to the template context.

**Risk:** Highest of all phases — touches every route. Do in one session, one commit, test all routes before proceeding.

---

### Phase 2 — Sidebar Shell (`base.html`)
**Scope:** Build the `base.html` Jinja2 template containing the full sidebar + site header layout. This is the direct translation of the approved `sidebar-flush.html` prototype into a Jinja2 template.

**Structure of `base.html`:**
```html
<body data-sidebar="{{ sidebar_state }}">
  <aside class="sidebar">
    <!-- Header: branding -->
    <!-- Content: nav groups with {% if active_nav == 'x' %} active states -->
    <!-- Rail: resize affordance div -->
    <!-- Footer: user info -->
  </aside>
  <div class="main-area">
    <header class="site-header">
      <!-- SidebarTrigger button -->
      <!-- Breadcrumb: {% block breadcrumb %} -->
      <!-- Header actions: {% block header_actions %} -->
    </header>
    <div class="page-content">
      {% block content %}{% endblock %}
    </div>
  </div>
</body>
```

**Context variables every route must pass:**
- `active_nav` — string key matching a nav item (`'browse'`, `'builds'`, `'templates'`, etc.)
- `breadcrumb` — list of `(label, url)` tuples; last item's url is `None` (renders as plain text)
- `page_title` — used in `<title>` tag

**CSS additions to `tonewood-dark.css`:**
```css
:root {
  --sidebar-width: 232px;
  --sidebar-width-collapsed: 52px;
  --sidebar-transition: 220ms cubic-bezier(0.4, 0, 0.2, 1);
  --header-height: 48px;
}
/* Collapsed state rules scoped to [data-sidebar="collapsed"] body */
/* Nav item active state via .nav-item--active class */
/* Tooltip positioning for collapsed icon-only mode */
```

---

### Phase 3 — Sidebar Collapse Behaviour (JS)
**Scope:** Implement the `collapsible="icon"` behaviour in vanilla JS. Add to `tonewood-app.js` or a new `sidebar.js`.

**Behaviour spec (translated from shadcn source):**

| State | Sidebar width | Labels | Icons |
|---|---|---|---|
| Expanded | 232px | Visible | Visible |
| Collapsed | 52px | `opacity: 0`, `width: 0` | Centred |

**Implementation (~80 lines JS):**
```javascript
// On page load: restore state from localStorage
// Toggle: flip data-sidebar attribute on <body>, save to localStorage  
// Keyboard: Ctrl+B / Cmd+B triggers toggle
// Tooltip: CSS-only via [data-tooltip] + ::after pseudo-element
//          Positioned right of sidebar using left: calc(var(--sidebar-width-collapsed) + 8px)
```

**Keyboard shortcut:** `Ctrl+B` (Windows/Linux) / `Cmd+B` (macOS) — matches shadcn's `SIDEBAR_KEYBOARD_SHORTCUT = "b"`.

**Mobile (< 768px):** Sidebar hides fully off-canvas. Toggle button shows it as a full-height overlay drawer with backdrop. Not in scope for initial implementation but the CSS groundwork is laid.

---

### Phase 4 — Build Planner Navigation Integration
**Scope:** Remove the Build Planner's isolated header and tab bar. Integrate its navigation into the unified sidebar.

**Before:** Build Planner had its own header (`🔨 Build Planner`) with a "← Tonewood Finder" back-link, and a `Builds | Templates` tab row below it.

**After:**
- "Build Planner" is a sidebar nav item (`active_nav='builds'`)
- "Templates" is a separate sidebar nav item (`active_nav='templates'`)  
- The `← Tonewood Finder` back-link is gone — the sidebar always shows where you are
- Build detail breadcrumb renders as: `Build Planner › Ash Jazz Project`
- "New Build" button moves to `{% block header_actions %}` in the site header

**No route or logic changes required.**

---

### Phase 5 — Filter Panel Adaptation (Browse Woods)
**Scope:** The Browse Woods page currently has a filter bar above the product table. In the new layout, it stays as a top-of-content filter bar (the simplest approach that keeps the table functional).

A right-side filter drawer (slide-in panel) is the ideal long-term pattern for maximising table width, but it adds JS complexity and is deferred as a follow-up improvement. The filter bar is adapted to sit cleanly inside the `{% block content %}` area with no other changes.

---

### Phase 6 — CSS Consolidation
**Scope:** Cleanup pass after all pages are migrated.

- Remove duplicated header/nav-tab CSS from both `tonewood-dark.css` and `builds.css` (replaced by the sidebar shell styles added in Phase 2)
- Verify all existing component styles (product table, build cards, part rows, picker modal, badge styles) still apply correctly within the new layout
- Confirm `builds.css` only contains build-specific component styles (no layout)

---

## 9. Effort & Session Plan

| Phase | Task | Complexity | Notes |1
|---|---|---|---|
| 1 | Jinja2 infrastructure + convert all routes | Medium-High | Single session, single commit. Highest risk. |
| 2 | `base.html` sidebar shell + CSS vars | Medium | Direct translation from approved prototype. |
| 3 | Collapse JS + keyboard shortcut | Low-Medium | ~80 lines. Independently testable. |
| 4 | Build Planner nav integration | Low | Template adjustments only, no route changes. |
| 5 | Filter bar adaptation | Low | Minimal CSS adjustment. |
| 6 | CSS consolidation + cleanup | Low | Cleanup pass, no new features. |

**Total estimated effort:** 3–4 focused Claude Code sessions, phases done sequentially. The app remains functional between phases — each phase is a clean, deployable increment.

---

## 10. File Change Summary

| File | Change |
|---|---|
| `app.py` | Routes: swap f-string returns for `render_template()`. Add `active_nav`, `breadcrumb`, `page_title` to each route's context. No logic changes. |
| `static/tonewood-dark.css` | Add sidebar shell CSS (vars, layout, nav items, collapse states, tooltip). Remove duplicated header/tab CSS. |
| `static/builds.css` | Remove duplicated header/tab CSS. Build component styles unchanged. |
| `static/tonewood-app.js` | Add sidebar toggle, localStorage persistence, keyboard shortcut. |
| `templates/base.html` | New file — the sidebar shell. |
| `templates/*.html` | New files — one per route, each extends `base.html`. |

No changes to: `models.py`, `import_data.py`, `fret_calc_excel.py`, `migrate_images.py`, `seed_templates.py`, any database files, or any Excel source files.

---

## 11. Open Items / Future Scope

- **Filter drawer (right slide-in panel):** Deferred from Phase 5. The ideal long-term pattern for the Browse Woods page — gives the product table full width while keeping filters accessible. Add after initial rollout.
- **Mobile sidebar (overlay drawer):** CSS groundwork laid in Phase 2/3 but full mobile implementation deferred.
- **Species Guide page** (`/species`): Nav item present in sidebar, route not yet built. Placeholder can be a simple "Coming soon" page that renders inside the shell.
- **Fret Calculator page** (`/fret`): Same — nav item present, route to be built.
- **Vendors page** (`/vendors`): Same.
- **Sidebar resize drag** (the `SidebarRail`): Visual affordance included in prototype. Full drag-to-resize via `mousedown`/`mousemove` is a stretch goal — deferred.
