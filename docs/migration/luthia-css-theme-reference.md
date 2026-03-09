# Luthia — CSS Theme System Reference

*Complete inventory of all colour tokens, custom properties, and per-component colour declarations*
*Extracted from `luthia-dark.css`, `luthia-light.css`, and `luthia-primary.css`*

Version 1.0 · March 2026

---

## 1. Three-File Architecture

| File | Purpose | Load order |
|---|---|---|
| `luthia-primary.css` | All structural rules (layout, sizing, spacing, typography, animation). **Zero colour properties.** | 1st |
| `luthia-dark.css` | Dark mode colour tokens + per-component colour declarations. Establishes default appearance. | 2nd |
| `luthia-light.css` | Light mode overrides scoped to `[data-mode="light"]`. Wins via selector specificity (0-2-0 vs 0-1-0). | 3rd |

**Switching mechanism:** `data-mode` and `data-theme` attributes on the `<html>` element. Theme/mode persisted in `localStorage`. No server round-trip required.

---

## 2. CSS Custom Properties (Design Tokens)

### 2.1 Accent Tokens — Per Theme × Per Mode

These three variables define the theme's primary colour and are the only tokens that change per theme.

#### Dark Mode (default)

| Token | Beeswax | Amber (default) | Maple | Mahogany | Spruce |
|---|---|---|---|---|---|
| `--accent` | `#f5c842` | `#e6a817` | `#c97c2a` | `#b5622a` | `#d4a574` |
| `--accent-dim` | `rgba(245,200,66,0.12)` | `rgba(230,168,23,0.12)` | `rgba(201,124,42,0.12)` | `rgba(181,98,42,0.12)` | `rgba(212,165,116,0.12)` |
| `--accent-text` | `#0e0e10` | `#0e0e10` | `#f4f4f5` | `#f4f4f5` | `#0e0e10` |

**Note:** `--accent-text` flips between dark (`#0e0e10`) and light (`#f4f4f5`) to ensure readable contrast on accent-coloured buttons. Beeswax, Amber, and Spruce are bright enough to use dark text; Maple and Mahogany are dark enough to need light text.

#### Light Mode

| Token | Beeswax | Amber (default) | Maple | Mahogany | Spruce |
|---|---|---|---|---|---|
| `--accent` | `#b89a00` | `#c48b0a` | `#a85e14` | `#9a4118` | `#8c6440` |
| `--accent-dim` | `rgba(184,154,0,0.10)` | `rgba(196,139,10,0.10)` | `rgba(168,94,20,0.10)` | `rgba(154,65,24,0.10)` | `rgba(140,100,64,0.10)` |
| `--accent-text` | `#ffffff` | `#ffffff` | `#ffffff` | `#ffffff` | `#ffffff` |

**Note:** All light mode accents are darkened for contrast against white/light backgrounds. All use white (`#ffffff`) for accent-text since every light-mode accent is dark enough.

#### Swatch Colours (for the theme picker dots)

These are set via `--swatch-color` inline on each swatch button:

| Theme | Swatch colour |
|---|---|
| Beeswax | `#f5c842` |
| Amber | `#e6a817` |
| Maple | `#c97c2a` |
| Mahogany | `#b5622a` |
| Spruce | `#d4a574` |

### 2.2 Component Tokens — Mode-Dependent

These tokens are shared across all themes and change only between dark and light mode. They provide the base palette that all component-level colour rules reference.

| Token | Dark Mode | Light Mode | Usage |
|---|---|---|---|
| `--panel-bg` | `#18181b` | `#ffffff` | Cards, sidebar, header, modals |
| `--border-color` | `#27272a` | `#e7e5e4` | Default borders |
| `--text-primary` | `#f4f4f5` | `#1c1917` | Headings, primary text |
| `--text-secondary` | `#d4d4d8` | `#44403c` | Body text, descriptions |
| `--text-muted` | `#52525b` | `#a8a29e` | Labels, placeholders, subtle text |
| `--hover-bg` | `rgba(255,255,255,0.06)` | `rgba(0,0,0,0.04)` | Interactive hover state |
| `--input-bg` | `rgba(255,255,255,0.06)` | `#fafaf9` | Form field backgrounds |
| `--surface-2` | `rgba(255,255,255,0.04)` | `rgba(0,0,0,0.03)` | Subtle raised surface |

### 2.3 Light Mode Extended UI Tokens

Light mode defines an additional `--ui-*` tier. These are declared but **not consistently referenced** by component rules (most light-mode component rules use hardcoded hex values matching these). Included here for completeness and as the canonical light palette:

| Token | Value | Tailwind stone equivalent | Usage |
|---|---|---|---|
| `--ui-bg` | `#f5f5f4` | stone-50 | Page background |
| `--ui-surface` | `#ffffff` | white | Cards, sidebar, header |
| `--ui-surface-2` | `#fafaf9` | stone-50 variant | Table header, footer, raised surface |
| `--ui-surface-3` | `#f0efee` | — | Subtle surface variant |
| `--ui-border` | `#e7e5e4` | stone-200 | Default border |
| `--ui-border-2` | `#d6d3d1` | stone-300 | Strong/focus border |
| `--ui-text-1` | `#1c1917` | stone-900 | Primary text |
| `--ui-text-2` | `#44403c` | stone-600 | Secondary text |
| `--ui-text-3` | `#78716c` | stone-500 | Tertiary text |
| `--ui-text-4` | `#a8a29e` | stone-400 | Muted text |
| `--ui-text-5` | `#d6d3d1` | stone-300 | Disabled/ultra-muted text |

### 2.4 Layout Tokens (luthia-primary.css)

Non-colour structural tokens. Shared across all modes and themes.

| Token | Value | Usage |
|---|---|---|
| `--sidebar-width` | `232px` | Expanded sidebar width |
| `--sidebar-width-collapsed` | `52px` | Collapsed sidebar width |
| `--sidebar-transition` | `220ms cubic-bezier(0.4, 0, 0.2, 1)` | Sidebar expand/collapse animation |
| `--header-height` | `48px` | Site header height |

---

## 3. Base Palette — Hardcoded Colour Values

Many component rules use hardcoded hex values rather than CSS custom properties. This section catalogues the recurring palette used across both mode files.

### 3.1 Dark Mode Base Palette

| Hex | Zinc equivalent | Role | Used by |
|---|---|---|---|
| `#111113` | zinc-950 variant | Page background, deep surfaces | `body`, `.main-area`, `.filter-bar`, `.page-toolbar` |
| `#18181b` | zinc-900 | Panel/card background | `.sidebar`, `.site-header`, `.table-wrap`, `.build-card`, `.form-card`, `.parts-list` |
| `#1c1c1e` | zinc-900 variant | Hover background, input bg | `.nav-item:hover`, `.btn-sm`, `.edit-btn`, `.filter-select` |
| `#1f1f23` | zinc-800 variant | Subtle row borders | `tbody tr` borders, `.part-row`, `.picker-row`, `.ref-row` |
| `#27272a` | zinc-800 | Default border, dividers | Sidebar borders, `.nav-divider`, `.table-wrap` border, `.build-card` border |
| `#2e2e32` | zinc-700 variant | Input/button borders | `.filter-select` border, `.btn-sm` border, `.edit-btn` border |
| `#3f3f46` | zinc-700 | Strong border, focus states | `.filter-select.has-value`, `.sidebar-rail::after`, `.page-num.active` border |
| `#52525b` | zinc-600 | Muted text | Labels, `.nav-group-label`, `.breadcrumb-item`, `.footer-role` |
| `#71717a` | zinc-500 | Dimmed text | `.dim`, `.price-cur`, `.page-btn` colour, `.ref-row` |
| `#a1a1aa` | zinc-400 | Secondary text | `.nav-item`, `.brand-sub`, `.vendor-name`, `.chip` |
| `#d4d4d8` | zinc-300 | Body text | `.df-val`, `.detail-vendor-name` |
| `#f4f4f5` | zinc-100 | Primary text, headings | `.species-name`, `.price-val`, `.page-title`, `.build-card-title` |

### 3.2 Light Mode Base Palette

| Hex | Stone equivalent | Role | Used by |
|---|---|---|---|
| `#f5f5f4` | stone-50 | Page background | `body`, `.main-area`, `.page-toolbar`, `.nav-item:hover` bg |
| `#ffffff` | white | Surface/card background | `.sidebar`, `.site-header`, `.table-wrap`, `.build-card`, `.form-card` |
| `#fafaf9` | stone-50 variant | Raised surface, input bg | `thead th`, `.table-footer`, `.img-thumb-wrap`, `.edit-input` |
| `#f0efee` | — | Subtle surface / row border | `tbody tr` border, `.btn-cancel:hover`, `.page-num.active` bg |
| `#e7e5e4` | stone-200 | Default border | Sidebar, header, table, card borders |
| `#d6d3d1` | stone-300 | Strong border | `.filter-select` border, `.sidebar-rail::after`, focus borders |
| `#a8a29e` | stone-400 | Muted text | Labels, `.nav-group-label`, `.breadcrumb-item`, `.footer-role` |
| `#78716c` | stone-500 | Tertiary text | `.nav-item`, `.filter-label`, `.part-role`, `.dim` |
| `#44403c` | stone-600 | Secondary text | `.chip`, `.df-val`, `.detail-vendor-name`, `.results-bar strong` |
| `#1c1917` | stone-900 | Primary text, headings | `.species-name`, `.price-val`, `.page-title`, `.build-card-title` |

### 3.3 Semantic Colours (Shared Across Modes)

| Purpose | Dark Mode | Light Mode |
|---|---|---|
| **Success / In-stock** | `#34d399` (emerald-400) | `#10b981` (emerald-500) |
| **Error / Danger** text | `#f87171` (red-400) | `#dc2626` (red-600) |
| **Error** bg colour | `#ef4444` (red-500) | `#ef4444` (red-500) |
| **Warning** text | `#f59e0b` (amber-500) | `#b45309` (amber-700) |
| **Info / Notice** text | `#60a5fa` (blue-400) | `#0369a1` (sky-700) |
| **Edit/Blue accent** | `#3b82f6` (blue-500) | `#3b82f6` (blue-500) |
| **Edit button** bg | `#2563eb` (blue-600) | `#2563eb` (blue-600) |
| **Edit active** bg | `#0f1929` / `#1a2235` | `#eff6ff` (blue-50) |
| **Toggle on** | `#16a34a` (green-600) | `#16a34a` (green-600) |
| **CITES badge** | `#ef4444` | `#dc2626` |
| **Delete button** bg | `#ef4444` → hover `#dc2626` | `#ef4444` → hover `#dc2626` |

---

## 4. Category Badge Colours

Each product category has a unique colour scheme for its badge/tag.

| Category | Dark bg | Dark text | Dark border | Light bg | Light text | Light border |
|---|---|---|---|---|---|---|
| Body | `#2a1f14` | `#c4956a` | `#6b3f1f` | `#fdf3ea` | `#8b5a2b` | `#d4a06a` |
| Neck | `#2a1218` | `#c47a88` | `#6b2535` | `#fdf0f3` | `#8b3a4f` | `#d48090` |
| Fretboard | `#161616` | `#a0a0a0` | `#3a3a3a` | `#f5f5f5` | `#4a4a4a` | `#c0c0c0` |
| Top | `#2a1a10` | `#c49060` | `#6b3818` | `#fef5ec` | `#8b5230` | `#d49060` |
| Carpentry | `#1a1c20` | `#8a9aaa` | `#2e3a46` | `#f0f4f8` | `#3a5a6a` | `#9ab0c0` |
| Finished | `#241e10` | `#b8a060` | `#5a4a1a` | `#fdf8ea` | `#7a6020` | `#c8a840` |
| Default | `#1e1e1e` | `#8a8a8a` | `#383838` | `#f5f5f5` | `#5a5a5a` | `#c0c0c0` |

---

## 5. Typography (from luthia-primary.css)

| Role | Font family | Weight | Style | Size |
|---|---|---|---|---|
| Brand wordmark | `'Cormorant', 'Georgia', serif` | 600 | italic | 1rem (sidebar), 2rem (page title) |
| Brand tagline | (inherits from parent) | 400 | normal | 0.5rem |
| Body / UI text | `-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif` | 400 | normal | 14px |
| Filter labels | inherit | 600 | normal | 11px, uppercase, letter-spacing 0.07em |
| Section labels | inherit | 600–700 | normal | 10–11px, uppercase, letter-spacing 0.07–0.09em |
| Price values | inherit | 600 | normal | 13px (table), 36px (detail hero) |
| Nav group label | inherit | 600 | normal | 10px, uppercase, letter-spacing 0.08em |

---

## 6. Component Colour Map

Complete mapping of every component's colour declarations across both modes. Components using CSS custom property tokens (e.g. `var(--panel-bg)`) are noted — these will resolve correctly via the token system and don't need per-component overrides in Tailwind.

### 6.1 Shell & Navigation

| Component | Property | Dark | Light |
|---|---|---|---|
| `body` | background | `#111113` | `#f5f5f4` |
| `body` | color | `#f4f4f5` | `#1c1917` |
| `.sidebar` | background | `#18181b` | `#ffffff` |
| `.sidebar` | border-right | `#27272a` | `#e7e5e4` |
| `.sidebar` | border-top | `#27272a` | `#e7e5e4` |
| `.sidebar-header` | border-bottom | `#27272a` | `#e7e5e4` |
| `.brand-name` | color | `var(--accent)` | `var(--accent)` |
| `.brand-sub` | color | `#a1a1aa` | `#18181b` |
| `.sidebar-rail::after` | background | `#3f3f46` | `#d6d3d1` |
| `.nav-group-label` | color | `#52525b` | `#a8a29e` |
| `.nav-divider` | background | `#27272a` | `#e7e5e4` |
| `.nav-item` | color | `#a1a1aa` | `#78716c` |
| `.nav-item:hover` | background | `#1c1c1e` | `#f5f5f4` |
| `.nav-item:hover` | color | `#f4f4f5` | `#1c1917` |
| `.nav-item--active` | background | `var(--accent-dim)` | `var(--accent-dim)` |
| `.nav-item--active` | color | `var(--accent)` | `var(--accent)` |
| `.nav-icon` | color | `#52525b` | `#d6d3d1` |
| `.nav-item:hover .nav-icon` | color | `#a1a1aa` | `#78716c` |
| `.nav-badge` | color / bg | `var(--accent)` / `var(--accent-dim)` | same |
| `.sidebar-footer` | border-top | `#27272a` | `#e7e5e4` |
| `.footer-avatar` | bg / border / color | `var(--accent-dim)` / `var(--accent)` / `var(--accent)` | same |
| `.footer-name` | color | `#f4f4f5` | `#1c1917` |
| `.footer-role` | color | `#52525b` | `#a8a29e` |

### 6.2 Header & Breadcrumb

| Component | Property | Dark | Light |
|---|---|---|---|
| `.site-header` | background | `#18181b` | `#ffffff` |
| `.site-header` | border-top/bottom | `#27272a` | `#e7e5e4` |
| `.sidebar-trigger` | color | `#52525b` | `#a8a29e` |
| `.sidebar-trigger:hover` | bg / color | `#1c1c1e` / `#f4f4f5` | `#f5f5f4` / `#1c1917` |
| `.header-sep` | background | `#27272a` | `#e7e5e4` |
| `.breadcrumb-item` | color | `#52525b` | `#a8a29e` |
| `.breadcrumb-item a:hover` | color | `#a1a1aa` | `#78716c` |
| `.breadcrumb-sep` | color | `#52525b` | `#a8a29e` |
| `.breadcrumb-current` | color | `#f4f4f5` | `#1c1917` |

### 6.3 Main Content Area

| Component | Property | Dark | Light |
|---|---|---|---|
| `.main-area` | background | `#111113` | `#f5f5f4` |
| `.page-title` | color | `#f4f4f5` | `#1c1917` |
| `.page-title-sub` | color | `#52525b` | `#a8a29e` |
| `.page-toolbar` | background | `#111113` | `#f5f5f4` |
| `.page-toolbar` | border-bottom | `#27272a` | `#e7e5e4` |
| `.toolbar-stat` | color | `#52525b` | `#a8a29e` |
| `.toolbar-stat strong` | color | `#a1a1aa` | `#44403c` |
| `.toolbar-count` | color | `#52525b` | `#a8a29e` |
| `.toolbar-count strong` | color | `#a1a1aa` | `#44403c` |
| `.results-footer` | color | `#52525b` | `#a8a29e` |
| `.results-footer` | border-top | `#27272a` | `#e7e5e4` |

### 6.4 Filter Controls

| Component | Property | Dark | Light |
|---|---|---|---|
| `.filter-bar` | background | `#111113` | `#ffffff` |
| `.filter-bar` | border-bottom | `#27272a` | `#e7e5e4` |
| `.filter-label` | color | `#6b7280` | `#78716c` |
| `.filter-select/input` | background | `#1c1c1e` | `#ffffff` |
| `.filter-select/input` | border | `#2e2e32` | `#d6d3d1` |
| `.filter-select/input` | color | `#f4f4f5` | `#1c1917` |
| `.filter-select/input:focus` | border-color | `#52525b` | `#a8a29e` |
| `.filter-select.has-value` | border-color | `#3f3f46` | `#a8a29e` |

### 6.5 Chips

| Component | Property | Dark | Light |
|---|---|---|---|
| `.chip` | color / bg / border | `#a1a1aa` / `#27272a` / `#3f3f46` | `#44403c` / `#e7e5e4` / `#d6d3d1` |
| `.chip-x` | color | `#52525b` | `#a8a29e` |
| `.chip-x:hover` | color | `#f4f4f5` | `#1c1917` |
| `.chips-clear` | color | `#52525b` | `#a8a29e` |
| `.chips-clear:hover` | color | `#a1a1aa` | `#44403c` |

### 6.6 Table

| Component | Property | Dark | Light |
|---|---|---|---|
| `.table-wrap` | bg / border | `#18181b` / `#27272a` | `#ffffff` / `#e7e5e4` |
| `thead th` | bg / border / color | `#18181b` / `#27272a` / `#52525b` | `#fafaf9` / `#e7e5e4` / `#a8a29e` |
| `thead th:hover` | color | `#a1a1aa` | `#78716c` |
| `thead th.sorted` | color | `#a1a1aa` | `#78716c` |
| `tbody tr` | border-bottom | `#1f1f23` | `#f0efee` |
| `tbody tr:hover` | background | `#1c1c1e` | `#fafaf9` |
| `.species-name` | color | `#f4f4f5` | `#1c1917` |
| `.species-alias` | color | `#52525b` | `#a8a29e` |
| `.vendor-name` | color | `#a1a1aa` | `#78716c` |
| `.dim` | color | `#71717a` | `#a8a29e` |
| `.price-val` | color | `#f4f4f5` | `#1c1917` |
| `.price-cur` | color | `#52525b` | `#a8a29e` |
| `.table-footer` | border-top / bg | `#27272a` / `#18181b` | `#e7e5e4` / `#fafaf9` |
| `.footer-count` | color | `#52525b` | `#a8a29e` |

### 6.7 Pagination

| Component | Property | Dark | Light |
|---|---|---|---|
| `.page-btn, .page-num` | color / bg / border | `#71717a` / `#1c1c1e` / `#2e2e32` | `#78716c` / `#ffffff` / `#e7e5e4` |
| hover | color / border | `#f4f4f5` / `#52525b` | `#1c1917` / `#a8a29e` |
| `.page-num.active` | bg / color / border | `#27272a` / `#f4f4f5` / `#3f3f46` | `#f0efee` / `#1c1917` / `#d6d3d1` |
| `:disabled` | color / border | `#3f3f46` / `#27272a` | `#d6d3d1` / `#e7e5e4` |
| `.page-ellipsis` | color | `#3f3f46` | `#d6d3d1` |

### 6.8 Shimmer (Loading)

| Mode | Gradient |
|---|---|
| Dark | `linear-gradient(90deg, #1f1f23 25%, #27272a 50%, #1f1f23 75%)` |
| Light | `linear-gradient(90deg, #f0efee 25%, #e7e5e4 50%, #f0efee 75%)` |

### 6.9 Theme Switcher & Mode Toggle

| Component | Property | Dark | Light |
|---|---|---|---|
| `.theme-switcher` | border-top | `#27272a` | `#e7e5e4` |
| `.theme-switcher-label` | color | `#52525b` | `#a8a29e` |
| `.theme-swatch.active` | border / shadow | `#f4f4f5` / `rgba(255,255,255,0.15)` | `#1c1917` / `rgba(0,0,0,0.10)` |
| `.mode-toggle` | color | `#52525b` | `#a8a29e` |
| `.mode-toggle:hover` | bg / color / border | `#27272a` / `#f4f4f5` / `#3f3f46` | `#f0efee` / `#44403c` / `#d6d3d1` |

---

## 7. Known Issues & Cleanup Notes

1. **Duplicate patch blocks:** All three CSS files contain the "Unified page layout" patch appended 2–3 times. The `.page-toolbar`, `.toolbar-stat`, `.toolbar-count`, `.results-footer`, `.sg-avail-badge`, and `.page-wrap` rules are duplicated. These should be deduplicated before migration.

2. **Dark CSS header comment mislabelled:** The header block in `luthia-dark.css` describes the light palette values (stone-50, #f5f5f4, etc.) — this is a copy-paste artefact from `luthia-light.css`.

3. **Inconsistent token usage:** Some components use CSS custom property tokens (`var(--panel-bg)`) while parallel components use hardcoded hex values. The Fret Calculator, Species Guide, and Vendor pages consistently use tokens; the Browse table, Builds page, and core layout use hardcoded hex. The Tailwind migration is an opportunity to normalise this by mapping everything through the design token layer.

4. **Light-mode `--ui-*` tokens declared but underused:** The `--ui-bg`, `--ui-surface`, `--ui-text-*` variables are defined but most light-mode component rules use matching hardcoded hex values instead of referencing these tokens. The Tailwind conversion should map through a single canonical token set.

5. **No dark-mode `--ui-*` equivalent:** Dark mode only declares the 7 component tokens (`--panel-bg`, etc.) plus the 3 accent tokens. There's no `--ui-bg`, `--ui-surface`, etc. tier for dark mode. The Tailwind migration should unify both modes under the same token names.

---

*Luthia · luthia.app · Where tone begins · CSS Theme Reference v1.0 · March 2026*
