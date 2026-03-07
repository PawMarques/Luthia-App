# API Routes Audit — Response Fields & Foreign Key Issues

Generated: 2026-03-06

---

## Overview

This document catalogs all API endpoints and the fields they return. **Flagged items** indicate endpoints that return only foreign key IDs where the frontend would need to resolve names separately, creating potential data fetching issues.

---

## ⚠️ Pagination Status Summary

| Endpoint | Pagination | Per-Page | Notes |
|----------|-----------|----------|-------|
| `GET /api/v1/products` | ✅ | 50 | Returns: `total`, `page`, `pages` |
| `GET /api/v1/species` | ✅ | 48 | Returns: `total`, `page`, `pages`, `per_page` |
| `GET /api/v1/vendors` | ❌ | N/A | **Returns full array** — no pagination metadata |
| `GET /api/v1/builds/<id>/candidates/<role>` | ❌ | N/A | **Returns full array** — no pagination metadata |

### Issues Found

🚩 **Two list endpoints lack pagination:**

1. **`GET /api/v1/vendors`** — Returns all vendors in a single array
   - OK for small vendor lists, but no metadata for client-side pagination UI

2. **`GET /api/v1/builds/<id>/candidates/<role>`** — Returns all candidate products in a single array
   - Could be problematic if a build has many matching products in a category
   - No way for frontend to implement "Load more" or page navigation

---

## 📁 browse.py

### `GET /api/v1/products` (Browse – Products List)

**Returns:** JSON object
```json
{
  "total": number,
  "page": number,
  "pages": number,
  "rows": [
    {
      "product_id": number,
      "species": string (resolved name),
      "alias": string,
      "vendor": string (resolved name),
      "vendor_flag": string (emoji),
      "category": string (resolved name),
      "cat_class": string,
      "format": string (resolved name or empty),
      "grade": string (resolved name or empty),
      "price": number,
      "url": string,
      "stale_date": string,
      "stale_color": string
    }
  ],
  "formats": [
    {
      "id": number,
      "name": string,
      "count": number
    }
  ]
}
```

**Status:** ✅ **GOOD** — All FK references resolved to names.

---

### `GET /api/v1/products/<id>` (Browse – Product Detail)

**Returns:** JSON object
```json
{
  "product_id": number,
  "price": number,
  "currency": string,
  "in_stock": boolean,
  "species_as_listed": string,
  "thickness_mm": number | null,
  "width_mm": number | null,
  "length_mm": number | null,
  "weight_kg": number | null,
  "url": string,
  "stale_date": string,
  "stale_color": string,
  "dimensions": string (formatted),
  "category": string (resolved name),
  "cat_class": string,
  "format": string (resolved name or empty),
  "grade": string (resolved name or empty),
  "unit": string (resolved name or empty),
  "vendor": string (resolved name),
  "vendor_flag": string (emoji),
  "vendor_country": string,
  "vendor_website": string,
  "vendor_currency": string,
  "scientific_name": string,
  "commercial_name": string,
  "alt_commercial_name": string,
  "english_name": string,
  "alt_english_name": string,
  "swedish_name": string,
  "alt_swedish_name": string,
  "portuguese_name": string,
  "alt_portuguese_name": string,
  "origin": string,
  "cites_listed": boolean,
  "aliases": {
    "[language]": [string, ...]
  },
  "images": [
    {
      // See images.py fmt_image() serialization
    }
  ]
}
```

**Status:** ✅ **GOOD** — All FK references fully resolved.

---

### `PUT /api/v1/products/<id>` (Browse – Product Edit)

**Request:** JSON with partial fields (price, in_stock, dimensions, product_url, format, grade)

**Returns:** JSON object
```json
{
  "ok": boolean,
  "errors": [string, ...] (only on failure)
}
```

**Status:** ✅ **GOOD** — No response data to validate.

---

## 📁 species.py

### `GET /api/v1/species` (Species List)

**Returns:** JSON object
```json
{
  "total": number,
  "page": number,
  "pages": number,
  "per_page": number,
  "rows": [
    {
      "species_id": number,
      "scientific_name": string,
      "commercial_name": string,
      "alt_commercial_name": string,
      "english_name": string,
      "alt_english_name": string,
      "swedish_name": string,
      "alt_swedish_name": string,
      "portuguese_name": string,
      "alt_portuguese_name": string,
      "origin": string,
      "cites_listed": boolean,
      "total_products": number,
      "in_stock_count": number,
      "vendors": [
        {
          "name": string (resolved),
          "flag": string (emoji)
        }
      ],
      "categories": [string, ...] (resolved names),
      "min_price": number,
      "max_price": number
    }
  ]
}
```

**Status:** ✅ **GOOD** — All FK references resolved to names and objects.

---

### `GET /api/v1/species/<id>` (Species Detail)

**Returns:** JSON object
```json
{
  "species_id": number,
  "scientific_name": string,
  "commercial_name": string,
  "alt_commercial_name": string,
  "english_name": string,
  "alt_english_name": string,
  "swedish_name": string,
  "alt_swedish_name": string,
  "portuguese_name": string,
  "alt_portuguese_name": string,
  "origin": string,
  "cites_listed": boolean,
  "aliases": {
    "[language]": [string, ...]
  },
  "products_by_cat": {
    "[category_name]": [
      {
        "product_id": number,
        "vendor": string (resolved name),
        "vendor_flag": string (emoji),
        "format": string (resolved name or empty),
        "grade": string (resolved name or empty),
        "price": number,
        "currency": string,
        "in_stock": boolean
      }
    ]
  },
  "total_products": number,
  "in_stock_count": number,
  "vendor_names": [
    {
      "name": string (resolved),
      "flag": string (emoji)
    }
  ],
  "categories": [string, ...] (resolved names),
  "min_price": number,
  "max_price": number
}
```

**Status:** ✅ **GOOD** — All FK references fully resolved.

---

## 📁 vendors.py

### `GET /api/v1/vendors` (Vendors List)

**Returns:** JSON array
```json
[
  {
    "vendor_id": number,
    "name": string,
    "country": string,
    "currency": string,
    "website": string,
    "active": boolean,
    "product_count": number,
    "flag": string (emoji, derived from country)
  }
]
```

**Status:** ✅ **GOOD** — No unresolved FK IDs. Currency and country codes are expected data.

---

### `POST /api/v1/vendors` (Create Vendor)

**Request:** JSON with name, country?, currency?, website?

**Returns:** JSON object
```json
{
  "ok": boolean,
  "vendor": { ... (same structure as GET list) }
}
```

**Status:** ✅ **GOOD** — Vendor object fully resolved.

---

### `PATCH /api/v1/vendors/<id>` (Update Vendor)

**Request:** JSON with partial fields (name, country, currency, website, active)

**Returns:** JSON object
```json
{
  "ok": boolean,
  "vendor": { ... (same structure as GET list) }
}
```

**Status:** ✅ **GOOD** — Vendor object fully resolved.

---

### `DELETE /api/v1/vendors/<id>` (Toggle Vendor Active)

**Returns:** JSON object
```json
{
  "ok": boolean,
  "vendor": { ... (same structure as GET list) }
}
```

**Status:** ✅ **GOOD** — Vendor object fully resolved.

---

## 📁 builds.py

### `GET /api/v1/builds/<id>/candidates/<role>` (Build Candidates for Part Role)

**Returns:** JSON array
```json
[
  {
    "id": number (product_id),
    "species": string (resolved name),
    "vendor": string (resolved name),
    "flag": string (emoji),
    "grade": string (resolved name or empty),
    "price": number,
    "dims": string (formatted),
    "dims_unverified": boolean,
    "url": string
  }
]
```

**Status:** ✅ **GOOD** — All FK references resolved to names.

---

### `PATCH /api/v1/builds/<id>/parts/<part_id>` (Assign Product to Part)

**Request:** JSON
```json
{
  "product_id": number | null
}
```

**Returns:** JSON object
```json
{
  "ok": boolean,
  "total": number (total price of build)
}
```

**Status:** ⚠️ **LIMITED DATA** — Returns only the total price. Frontend needs to:
- Fetch updated product details separately if it wants to display them
- Or track locally after assignment

**Note:** Not technically a FK ID issue, but a data minimality issue. The response could include the product details or at least a flag indicating the assignment status, but this is acceptable for a PATCH endpoint.

---

### `DELETE /api/v1/builds/<id>` (Delete Build)

**Returns:** JSON object
```json
{
  "ok": boolean
}
```

**Status:** ✅ **GOOD** — Status-only response appropriate for DELETE.

---

## 📁 images.py

### `POST /api/v1/products/<id>/images` (Upload or URL Image)

**Request:**
- Multipart form-data (file upload) or
- JSON `{url, caption?}`

**Returns:** JSON object
```json
{
  "ok": boolean,
  "image": {
    "image_id": number,
    "source_type": string ("upload" | "url"),
    "src": string (resolved URL: /uploads/{filename} or external URL),
    "caption": string,
    "sort_order": number
  }
}
```

**Status:** ✅ **GOOD** — Image object fully resolved with direct URLs.

---

### `DELETE /api/v1/images/<id>` (Delete Image)

**Returns:** JSON object
```json
{
  "ok": boolean
}
```

**Status:** ✅ **GOOD** — Status-only response appropriate for DELETE.

---

### `PATCH /api/v1/images/<id>/caption` (Update Caption)

**Request:** JSON
```json
{
  "caption": string
}
```

**Returns:** JSON object
```json
{
  "ok": boolean
}
```

**Status:** ✅ **GOOD** — Status-only response appropriate for PATCH.

---

## 📁 fret.py

### `GET /api/v1/fret/calculate` (Calculate Fret Positions)

**Query params:** scale_mm (required), num_frets (default 24)

**Returns:** JSON object
```json
{
  "ok": boolean,
  "scale_mm": number,
  "num_frets": number,
  "frets": [
    {
      "fret": number,
      "from_nut_mm": number,
      "from_nut_in": number,
      "spacing_mm": number | null,
      "spacing_in": number | null
    }
  ]
}
```

**Status:** ✅ **GOOD** — Pure calculation data, no FK references.

---

### `GET /api/v1/fret/export` (Export Fret Table as Excel)

**Query params:** scale_mm, num_frets, label?

**Returns:** Binary XLSX file (streaming download)

**Status:** ✅ **GOOD** — File response, no data structure to validate.

---

## 📁 templates.py

**Note:** All endpoints in this file are page routes (HTML rendering), not JSON APIs.

- `GET /templates` — Renders HTML template index
- `GET /templates/<id>/edit` — Renders HTML edit form
- `POST /templates/<id>/edit` — Form submission, redirects to /templates

**Status:** N/A — No API endpoints.

---

## Summary of Issues

| Issue Type | Count | Details |
|-----------|-------|---------|
| **Unresolved FK IDs** | **0** | ✅ **All API endpoints return fully resolved names** |
| **Missing Pagination** | **2** | ⚠️ `/api/v1/vendors` and `/api/v1/builds/<id>/candidates/<role>` return full arrays without pagination metadata |
| **Data Minimality** | 1 | `PATCH /api/v1/builds/<id>/parts/<part_id>` returns only total price (acceptable for PATCH) |
| **Missing Data** | 0 | ✅ All image, product, species, and vendor data is complete |

### Key Findings

✅ **No FK ID Flagging Needed** — The API is well-designed:
- All browse/detail endpoints return resolved names (species, vendor, category, format, grade, unit)
- Image responses return resolved URLs, not FK IDs
- Vendor data includes computed derived fields (flag emoji)
- Product candidates in builds include fully resolved product details

✅ **Pagination Implemented Where Needed** — Primary list endpoints:
- `/api/v1/products` ✅ 50 items/page with total, page, pages metadata
- `/api/v1/species` ✅ 48 items/page with total, page, pages, per_page metadata

⚠️ **Pagination Gaps** (not critical but worth noting):
- `/api/v1/vendors` returns **full array** without pagination
  - Acceptable if vendor count stays small, but no metadata for client-side paging UI
- `/api/v1/builds/<id>/candidates/<role>` returns **full array** without pagination
  - Could be problematic with large product databases (hundreds of candidates per role)

✅ **Frontend Friendly** — No cascading fetch requirements:
- Browse products: get species, vendor, category, grade, format names directly
- Product detail: get all related names and image URLs without N+1 queries
- Species detail: get vendor names and categories in one response
- Builds candidates: get all product info without separate lookups

⚠️ **Minor Observations** (not issues):
1. `PATCH /api/v1/builds/<id>/parts/<part_id>` returns minimal data (just `{ok, total}`), but this is appropriate for a PATCH endpoint; frontend tracks the product_id in the request
2. Build part assignment doesn't return product details, requiring frontend to either cache or fetch separately if displaying updated product info

### Recommendations

1. **No FK ID issues to resolve** — The API architecture is excellent with resolved data throughout.

2. **Consider paginating vendor and candidates lists** (optional):
   - **`/api/v1/vendors`** — Add pagination metadata if vendor count grows beyond ~100 items
   - **`/api/v1/builds/<id>/candidates/<role>`** — Add pagination if product databases scale significantly
   - Both could support `?page=N&limit=50` query params while maintaining backward compatibility

3. **Frontend consideration** — When displaying build parts after assignment, either cache the product object locally or fetch from a separate detail endpoint if needed.

4. **Documentation** — Consider adding JSDoc/TypeScript interfaces documenting these response shapes for frontend developers.

