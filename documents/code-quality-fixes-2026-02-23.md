# Code Quality Fixes — 2026-02-23

## Summary

Two minor code quality issues were resolved across three files. All 67 tests pass after the changes.

---

## Fix 1 — Deferred import moved to top-level (`routes/images.py`)

**Problem:** `from models import Product` was placed inside the body of `api_image_upload()` rather than at the top of the module with the other model imports. Deferred imports are harder to spot during code review and mask missing-module errors until the specific route is exercised at runtime.

**Change:**

```python
# Before — line 15
from models import ProductImage, db

# Inside api_image_upload():
from models import Product          # ← deferred
Product.query.get_or_404(product_id)

# After — line 15
from models import Product, ProductImage, db

# Inside api_image_upload():
Product.query.get_or_404(product_id)  # ← deferred import removed
```

**Files changed:** `routes/images.py`

---

## Fix 2 — Replace deprecated `datetime.utcnow()` (`helpers.py`, `routes/browse.py`)

**Problem:** `datetime.utcnow()` is deprecated since Python 3.12 and emits `DeprecationWarning` in newer interpreters. It returns a naïve datetime with no timezone attached, and the deprecation note recommends switching to the aware equivalent `datetime.now(timezone.utc)`.

**Approach:** Replace with `datetime.now(timezone.utc).replace(tzinfo=None)`. Stripping the timezone info with `.replace(tzinfo=None)` keeps the result naïve, so existing SQLite timestamp comparisons continue to work without any schema migration.

`timezone` was added to the `from datetime import ...` line in both files.

### `helpers.py` — `staleness_info()`

```python
# Before
from datetime import datetime

age_months = (datetime.utcnow() - last_updated).days / 30.4

# After
from datetime import datetime, timezone

age_months = (datetime.now(timezone.utc).replace(tzinfo=None) - last_updated).days / 30.4
```

### `routes/browse.py` — `api_product_edit()`

```python
# Before
from datetime import datetime

p.last_updated = datetime.utcnow()

# After
from datetime import datetime, timezone

p.last_updated = datetime.now(timezone.utc).replace(tzinfo=None)
```

**Files changed:** `helpers.py`, `routes/browse.py`

---

## Test mock updates (`tests/test_helpers.py`)

The three `staleness_info` tests patched `helpers.datetime` and accessed `.utcnow.return_value`. After the production code switched to `.now(...).replace(tzinfo=None)`, the mocks were updated to match the new call chain:

```python
# Before
mock_dt.utcnow.return_value = fixed_now

# After
mock_dt.now.return_value.replace.return_value = fixed_now
```

**Files changed:** `tests/test_helpers.py`

---

## Test results

```
67 passed, 25 warnings in 0.26s
```

All warnings are pre-existing `LegacyAPIWarning` from SQLAlchemy's `Query.get()` and are unrelated to these changes.
