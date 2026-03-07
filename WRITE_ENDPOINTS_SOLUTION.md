# Write Endpoints Solution Proposal

**Date:** 2026-03-07

---

## Overview

This document proposes solutions to return complete updated objects from write endpoints instead of success-only flags.

---

## Problem Statement

Three write endpoints lack complete response data:

1. **`PUT /api/v1/products/<id>`** — Returns `{ok: true}` (no product data)
2. **`PATCH /api/v1/images/<id>/caption`** — Returns `{ok: true}` (no image data)
3. **`PATCH /api/v1/builds/<id>/parts/<part_id>`** — Returns `{ok: true, total}` (no part/product data)

**Impact:**
- Frontend cannot optimistically update UI
- Requires additional fetch calls to display changes
- Inconsistent with vendor endpoint pattern
- No server confirmation of actual values saved

---

## Solution 1: `PUT /api/v1/products/<id>` (Edit Product)

### Current Response
```json
{
  "ok": true
}
```

### Proposed Response
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
    "format": string (resolved name),
    "grade": string (resolved name),
    "last_updated": string (ISO 8601)
  }
}
```

### Implementation

**File:** `luthia-server/routes/browse.py`

**Change Location:** [api_product_edit()](luthia-server/routes/browse.py#L310)

**Current Code:**
```python
if errors:
    return jsonify({'ok': False, 'errors': errors}), 400

p.last_updated = datetime.now(timezone.utc).replace(tzinfo=None)
db.session.commit()
return jsonify({'ok': True})
```

**Proposed Code:**
```python
if errors:
    return jsonify({'ok': False, 'errors': errors}), 400

p.last_updated = datetime.now(timezone.utc).replace(tzinfo=None)
db.session.commit()

# Return updated product data
updated_product = {
    'product_id': p.product_id,
    'price': round(p.price, 2),
    'in_stock': p.in_stock,
    'thickness_mm': p.thickness_mm,
    'width_mm': p.width_mm,
    'length_mm': p.length_mm,
    'weight_kg': p.weight_kg,
    'product_url': p.product_url or '',
    'format': p.format.name if p.format else '',
    'grade': p.grade.name if p.grade else '',
    'last_updated': p.last_updated.isoformat() if p.last_updated else '',
}
return jsonify({'ok': True, 'product': updated_product})
```

### Frontend Benefit

**Before (requires re-fetch):**
```typescript
const response = await fetch(`/api/v1/products/${productId}`, {
  method: 'PUT',
  body: JSON.stringify({ price: 100.50 })
});
if (response.ok) {
  // Must re-fetch to show updated data
  const detail = await fetch(`/api/v1/products/${productId}`);
  const product = await detail.json();
  updateUI(product);
}
```

**After (use response immediately):**
```typescript
const response = await fetch(`/api/v1/products/${productId}`, {
  method: 'PUT',
  body: JSON.stringify({ price: 100.50 })
});
const { product } = await response.json();
updateUI(product); // No additional fetch needed
```

### Effort
- **Low** — Simple restructuring of existing data
- No new database queries
- Reuse existing serialization logic

---

## Solution 2: `PATCH /api/v1/images/<id>/caption` (Update Caption)

### Current Response
```json
{
  "ok": true
}
```

### Proposed Response
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

### Implementation

**File:** `luthia-server/routes/images.py`

**Change Location:** [api_image_caption()](luthia-server/routes/images.py#L62)

**Current Code:**
```python
@images_bp.route('/api/v1/images/<int:image_id>/caption', methods=['PATCH'])
def api_image_caption(image_id):
    """Update the caption text of an existing image."""
    img = ProductImage.query.get_or_404(image_id)
    data = request.get_json(force=True)
    img.caption = (data.get('caption') or '').strip()
    db.session.commit()
    return jsonify({'ok': True})
```

**Proposed Code:**
```python
@images_bp.route('/api/v1/images/<int:image_id>/caption', methods=['PATCH'])
def api_image_caption(image_id):
    """Update the caption text of an existing image."""
    img = ProductImage.query.get_or_404(image_id)
    data = request.get_json(force=True)
    img.caption = (data.get('caption') or '').strip()
    db.session.commit()
    return jsonify({'ok': True, 'image': fmt_image(img)})
```

**That's it!** The `fmt_image()` helper already returns the exact structure we need.

### Frontend Benefit

**Before:**
```typescript
const response = await fetch(`/api/v1/images/${imageId}/caption`, {
  method: 'PATCH',
  body: JSON.stringify({ caption: 'New caption' })
});
// No way to verify what was saved
```

**After:**
```typescript
const response = await fetch(`/api/v1/images/${imageId}/caption`, {
  method: 'PATCH',
  body: JSON.stringify({ caption: 'New caption' })
});
const { image } = await response.json();
console.log(image.caption); // Confirm the saved value
updateImageUI(image);
```

### Effort
- **Minimal** — One-line change
- Reuses existing `fmt_image()` helper
- Zero new logic required

---

## Solution 3: `PATCH /api/v1/builds/<id>/parts/<part_id>` (Assign Product to Part)

### Current Response
```json
{
  "ok": true,
  "total": number
}
```

### Proposed Response

**Option A: Minimal (Recommended)**
```json
{
  "ok": true,
  "part": {
    "part_id": number,
    "role": string,
    "product_id": number | null,
    "dims_unverified": boolean,
    "thickness_warning": boolean
  },
  "total": number
}
```

**Option B: Complete (Richer, but more data)**
```json
{
  "ok": true,
  "part": {
    "part_id": number,
    "role": string,
    "product_id": number | null,
    "product": {
      "product_id": number,
      "species": string,
      "vendor": string,
      "vendor_flag": string,
      "grade": string,
      "price": number,
      "dims": string,
      "url": string
    } | null,
    "dims_unverified": boolean,
    "thickness_warning": boolean
  },
  "total": number
}
```

### Recommendation
**Use Option A** — It includes the essential part state flags without duplicating product data (which frontend already has from the candidates list).

### Implementation

**File:** `luthia-server/routes/builds.py`

**Change Location:** [api_build_part_update()](luthia-server/routes/builds.py#L193)

**Current Code:**
```python
def api_build_part_update(build_id, part_id):
    """Assign a product to a build part slot and recompute all derived values."""
    build = Build.query.get_or_404(build_id)
    part  = BuildPart.query.filter_by(part_id=part_id, build_id=build_id).first_or_404()

    data       = request.get_json()
    product_id = data.get('product_id')
    part.product_id = product_id

    # Flag when the vendor hasn't published dimension data for this product.
    if product_id:
        p = Product.query.get(product_id)
        part.dims_unverified = not any([p.length_mm, p.width_mm, p.thickness_mm])
    else:
        part.dims_unverified = False

    _check_thickness_warning(build)
    build.compute_total()
    build.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.commit()

    return jsonify({'ok': True, 'total': build.total_price})
```

**Proposed Code:**
```python
def api_build_part_update(build_id, part_id):
    """Assign a product to a build part slot and recompute all derived values."""
    build = Build.query.get_or_404(build_id)
    part  = BuildPart.query.filter_by(part_id=part_id, build_id=build_id).first_or_404()

    data       = request.get_json()
    product_id = data.get('product_id')
    part.product_id = product_id

    # Flag when the vendor hasn't published dimension data for this product.
    if product_id:
        p = Product.query.get(product_id)
        part.dims_unverified = not any([p.length_mm, p.width_mm, p.thickness_mm])
    else:
        part.dims_unverified = False

    _check_thickness_warning(build)
    build.compute_total()
    build.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.commit()

    # Return updated part with all state flags
    part_data = {
        'part_id': part.part_id,
        'role': part.role,
        'product_id': part.product_id,
        'dims_unverified': part.dims_unverified,
        'thickness_warning': part.thickness_warning,
    }
    return jsonify({'ok': True, 'part': part_data, 'total': build.total_price})
```

**Alternative: Extract to Helper Function**
```python
def _build_part_dict(part: BuildPart) -> dict:
    """Serialise a BuildPart for API responses."""
    return {
        'part_id': part.part_id,
        'role': part.role,
        'product_id': part.product_id,
        'dims_unverified': part.dims_unverified,
        'thickness_warning': part.thickness_warning,
    }

def api_build_part_update(build_id, part_id):
    # ... existing code ...
    return jsonify({'ok': True, 'part': _build_part_dict(part), 'total': build.total_price})
```

### Frontend Benefit

**Before (no part data, forced to manage local state):**
```typescript
const [parts, setParts] = useState(initialParts);

const assignProduct = async (partId, productId) => {
  const response = await fetch(`/api/v1/builds/${buildId}/parts/${partId}`, {
    method: 'PATCH',
    body: JSON.stringify({ product_id: productId })
  });
  const { total } = await response.json();

  // Must manually update local part (risk of sync issues)
  setParts(parts.map(p =>
    p.part_id === partId
      ? { ...p, product_id: productId }
      : p
  ));
  setTotal(total);
};
```

**After (full part state confirmed by server):**
```typescript
const [parts, setParts] = useState(initialParts);

const assignProduct = async (partId, productId) => {
  const response = await fetch(`/api/v1/builds/${buildId}/parts/${partId}`, {
    method: 'PATCH',
    body: JSON.stringify({ product_id: productId })
  });
  const { part, total } = await response.json();

  // Update from server-confirmed state
  setParts(parts.map(p =>
    p.part_id === part.part_id
      ? part  // Use server response, not request
      : p
  ));
  setTotal(total);
};
```

### Effort
- **Low** — Simple object serialization
- No new queries (all data already loaded)
- Optional: Extract `_build_part_dict()` helper for consistency

---

## Implementation Priority & Effort Matrix

| Issue | Priority | Effort | Impact | Recommendation |
|-------|----------|--------|--------|-----------------|
| Product edit | 🔴 High | Low | High (affects inline editing) | Implement immediately |
| Image caption | 🔴 High | Minimal | Medium (verification + UX) | Implement immediately |
| Build part assign | 🟡 Medium | Low | Medium (part state sync) | Implement in same PR |

---

## Implementation Plan

### Phase 1: Code Changes (1-2 hours)

1. **Update `browse.py`** — Modify `api_product_edit()` return statement
   - Add updated product serialization
   - Test with various field combinations

2. **Update `images.py`** — Modify `api_image_caption()` return statement
   - Single-line change to include `fmt_image(img)`
   - Test caption updates

3. **Update `builds.py`** — Modify `api_build_part_update()` return statement
   - Add part serialization
   - Consider extracting `_build_part_dict()` helper
   - Test with products that have/lack dimension data

### Phase 2: Frontend Testing (1-2 hours)

1. **Product browse detail view** — Verify inline edits update immediately
2. **Product images** — Verify caption changes show in UI
3. **Build planner** — Verify part assignments update with correct flags

### Phase 3: Backward Compatibility (Optional)

All changes are **backward compatible** — clients that ignore the new fields continue working:
- Existing clients checking only `ok: true` still work
- New clients can use the returned objects

No API versioning or breaking changes required.

---

## Testing Checklist

### Product Edit (`PUT /api/v1/products/<id>`)
- [ ] Edit price → verify returned price matches request
- [ ] Edit in_stock → verify returned value is boolean
- [ ] Edit dimensions → verify null values are returned as null
- [ ] Create new format → verify returned format name is set
- [ ] Create new grade → verify returned grade name is set
- [ ] Verify last_updated timestamp is current

### Image Caption (`PATCH /api/v1/images/<id>/caption`)
- [ ] Update caption → verify returned caption matches request
- [ ] Clear caption (empty string) → verify returned caption is empty
- [ ] Verify other image fields (image_id, src, sort_order) are unchanged
- [ ] Verify response matches structure of POST image response

### Build Part Assign (`PATCH /api/v1/builds/<id>/parts/<part_id>`)
- [ ] Assign product with dimensions → verify dims_unverified = false
- [ ] Assign product without dimensions → verify dims_unverified = true
- [ ] Assign product that triggers thickness warning → verify thickness_warning = true
- [ ] Clear product assignment → verify product_id = null, dims_unverified = false
- [ ] Verify total price is updated correctly

---

## Rollout Strategy

1. **Update all three endpoints** in a single PR
2. **Add tests** for the new response fields
3. **Update API documentation/OpenAPI spec** if applicable
4. **No frontend changes required initially** — return data is additive
5. **Optional frontend enhancement** in next sprint to use optimistic updates

---

## Benefits Summary

| Benefit | Impact |
|---------|--------|
| **Eliminates N+1 queries** | Frontend doesn't need follow-up fetches |
| **Enables optimistic updates** | Immediate UI feedback without round-trips |
| **Consistent API pattern** | All write endpoints return updated object (like vendors) |
| **Server-confirmed data** | No sync issues between client and server state |
| **Backward compatible** | No breaking changes to existing clients |
| **Better error handling** | Can verify exact values saved if validation happens server-side |

