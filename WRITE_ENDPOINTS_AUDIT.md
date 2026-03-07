# Write Endpoints Audit — POST/PATCH/PUT/DELETE Response Data

**Date:** 2026-03-07

---

## Summary

**Out of 9 write endpoints:**
- ✅ **4 return the updated object** — Vendor endpoints, Image upload
- ⚠️ **2 return partial data** — Build part update (only total price), Image caption (no data)
- ❌ **3 return only success flags** — Product edit, Build delete, Image delete

---

## Detailed Analysis

### ✅ GOOD: Returns Full Updated Object

#### `POST /api/v1/vendors` (Create Vendor)

**Location:** [vendors.py:85](luthia-server/routes/vendors.py#L85)

**Returns:**
```json
{
  "ok": true,
  "vendor": {
    "vendor_id": number,
    "name": string,
    "country": string,
    "currency": string,
    "website": string,
    "active": boolean,
    "product_count": number,
    "flag": string (emoji)
  }
}
```

**Status:** ✅ Includes full vendor details immediately after creation.

---

#### `PATCH /api/v1/vendors/<id>` (Update Vendor)

**Location:** [vendors.py:118](luthia-server/routes/vendors.py#L118)

**Returns:**
```json
{
  "ok": true,
  "vendor": {
    "vendor_id": number,
    "name": string,
    "country": string,
    "currency": string,
    "website": string,
    "active": boolean,
    "product_count": number,
    "flag": string (emoji)
  }
}
```

**Status:** ✅ Includes full vendor details after update.

---

#### `DELETE /api/v1/vendors/<id>` (Toggle Vendor Active)

**Location:** [vendors.py:133](luthia-server/routes/vendors.py#L133)

**Returns:**
```json
{
  "ok": true,
  "vendor": {
    "vendor_id": number,
    "name": string,
    "country": string,
    "currency": string,
    "website": string,
    "active": boolean,
    "product_count": number,
    "flag": string (emoji)
  }
}
```

**Status:** ✅ Includes full vendor details after toggling active flag.

---

#### `POST /api/v1/products/<id>/images` (Upload Image)

**Location:** [images.py:85, 114](luthia-server/routes/images.py#L85)

**Returns:**
```json
{
  "ok": true,
  "image": {
    "image_id": number,
    "source_type": string ("upload" | "url"),
    "src": string (resolved URL),
    "caption": string,
    "sort_order": number
  }
}
```

**Status:** ✅ Includes full image object immediately after creation.

---

### ⚠️ PARTIAL DATA: Returns Success + Partial Fields

#### `PATCH /api/v1/builds/<id>/parts/<part_id>` (Assign Product to Part)

**Location:** [builds.py:193](luthia-server/routes/builds.py#L193)

**Returns:**
```json
{
  "ok": true,
  "total": number (build total price only)
}
```

**What's Missing:**
- No part object returned
- No product details
- No dims_unverified flag
- No thickness_warning flag

**Frontend Impact:**
- Frontend must already have part/product details cached in state
- Must track only the total price update
- Cannot update part display without separate fetch

**Recommendation:** Consider enriching with:
```json
{
  "ok": true,
  "part": {
    "part_id": number,
    "role": string,
    "product_id": number,
    "dims_unverified": boolean,
    "thickness_warning": boolean
  },
  "total": number
}
```

---

### ❌ MISSING DATA: Returns Only Success Flag

#### `PUT /api/v1/products/<id>` (Edit Product)

**Location:** [browse.py:310](luthia-server/routes/browse.py#L310)

**Returns:**
```json
{
  "ok": true
}
```

**What's Missing:**
- No updated product object
- No confirmation of which fields were changed
- Frontend must either re-fetch or maintain local state

**Editable Fields:**
- `price`
- `in_stock`
- `thickness_mm`, `width_mm`, `length_mm`, `weight_kg`
- `product_url`
- `format` (creates/assigns if not exists)
- `grade` (creates/assigns if not exists)

**Frontend Impact:**
- Must re-fetch full product detail to show updated data in detail panel
- Cannot optimistically update inline without server confirmation

**Recommendation:** Return the updated product:
```json
{
  "ok": true,
  "product": {
    "product_id": number,
    "price": number,
    "in_stock": boolean,
    "thickness_mm": number | null,
    "width_mm": number | null,
    "length_mm": number | null,
    "weight_kg": number | null,
    "product_url": string,
    "format": string,
    "grade": string,
    "last_updated": string (ISO date)
  }
}
```

---

#### `DELETE /api/v1/builds/<id>` (Delete Build)

**Location:** [builds.py:202](luthia-server/routes/builds.py#L202)

**Returns:**
```json
{
  "ok": true
}
```

**What's Missing:**
- No build object or ID confirmation
- Frontend must rely on request to have the build_id

**Frontend Impact:**
- Acceptable for DELETE operations where the resource no longer exists
- Frontend knows the build_id from the request path
- Simple navigation away from the deleted build is sufficient

**Status:** ⚠️ Acceptable for DELETE, but could confirm the deleted build_id

---

#### `DELETE /api/v1/images/<id>` (Delete Image)

**Location:** [images.py:52](luthia-server/routes/images.py#L52)

**Returns:**
```json
{
  "ok": true
}
```

**What's Missing:**
- No confirmation of which image was deleted
- Frontend must rely on request to have the image_id

**Frontend Impact:**
- Acceptable for DELETE operations
- Frontend knows the image_id from the request path
- Image can be removed from local list optimistically

**Status:** ⚠️ Acceptable for DELETE, but could confirm the deleted image_id

---

#### `PATCH /api/v1/images/<id>/caption` (Update Image Caption)

**Location:** [images.py:62](luthia-server/routes/images.py#L62)

**Returns:**
```json
{
  "ok": true
}
```

**What's Missing:**
- No updated image object
- No confirmation of new caption
- Frontend must maintain local state or re-fetch

**Frontend Impact:**
- Cannot confirm the caption was actually saved
- Must update UI based on request data, not response

**Recommendation:** Return the updated image:
```json
{
  "ok": true,
  "image": {
    "image_id": number,
    "source_type": string,
    "src": string,
    "caption": string,
    "sort_order": number
  }
}
```

---

## Comparison Matrix

| Endpoint | Method | Returns Updated Object | Data Completeness | Recommendation |
|----------|--------|----------------------|-------------------|-----------------|
| Vendors (create) | POST | ✅ Yes | Complete | No change |
| Vendors (update) | PATCH | ✅ Yes | Complete | No change |
| Vendors (toggle) | DELETE | ✅ Yes | Complete | No change |
| Image (upload) | POST | ✅ Yes | Complete | No change |
| **Product (edit)** | **PUT** | **❌ No** | **None** | **Return updated product** |
| **Build part (assign)** | **PATCH** | **⚠️ Partial** | **Price only** | **Return part object with product details** |
| **Build (delete)** | **DELETE** | **⚠️ Minimal** | **Status only** | **Return deleted build_id (optional)** |
| **Image (delete)** | **DELETE** | **⚠️ Minimal** | **Status only** | **Return deleted image_id (optional)** |
| **Image (caption)** | **PATCH** | **❌ No** | **None** | **Return updated image** |

---

## Recommendations by Priority

### 🔴 High Priority (Affects UX/Data Sync)

1. **`PUT /api/v1/products/<id>`** — Return updated product object
   - Currently requires re-fetch to display changes
   - Should include: price, in_stock, dimensions, url, format, grade, last_updated

2. **`PATCH /api/v1/images/<id>/caption`** — Return updated image object
   - Currently no confirmation the update succeeded
   - Should include: image_id, source_type, src, caption, sort_order

### 🟡 Medium Priority (Improves Part Update Experience)

3. **`PATCH /api/v1/builds/<id>/parts/<part_id>`** — Return part object with product context
   - Currently returns only total price
   - Should include: part_id, role, product_id, dims_unverified, thickness_warning

### 🟢 Low Priority (Good-to-Have, DELETE Pattern)

4. **`DELETE /api/v1/builds/<id>`** — Consider returning deleted build_id
   - Currently just success flag (acceptable for DELETE)
   - Would help confirm which build was deleted

5. **`DELETE /api/v1/images/<id>`** — Consider returning deleted image_id
   - Currently just success flag (acceptable for DELETE)
   - Would help confirm which image was deleted

---

## Implementation Consistency

**Vendor endpoints** set the gold standard:
- All write operations return the updated/created object with all fields
- Frontend gets immediate confirmation of the change
- No separate fetch needed to display updated data

**Recommendation:** Align other write endpoints with this pattern.

