# Path Audit Report: data-sources/scripts/

**Date**: March 6, 2026
**Scope**: All Python files in `data-sources/scripts/`
**Status**: ✅ No hardcoded `luthia-app/` or `scripts/` references found

---

## Summary

The migration from `luthia-app/scripts/` to `data-sources/scripts/` has been successfully completed. **No hardcoded path references to the old locations were found.**

However, the scripts use fragile relative path traversal patterns (`../../luthia-data/`) that rely on understanding directory depth. These can be improved for clarity and maintainability.

---

## File-by-File Analysis

### 1. ✅ `create_github_project.py`
**Status**: Clean (GitHub automation, no file paths)
- No file I/O beyond token/config
- No path-dependent code

---

### 2. ⚠️ `fret_calc_excel.py`
**Output Path**: `../../luthia-data/fret_placement_tables.xlsx`

```python
# Line 96
output_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', 'luthia-data',
    'fret_placement_tables.xlsx'
)
```

**Issues**:
- Fragile relative path traversal (`../..`)
- Relies on understanding directory depth
- No explicit repo root reference

**Recommendation**: Use `pathlib.Path` with explicit repo root calculation

---

### 3. ⚠️ `import_data.py`
**Input Paths**:
- Database: `../../luthia-data/luthia.db` (line 13)
- Data sources: `../../data-sources/` (line 649)

```python
# Lines 12-13
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(
    os.path.dirname(os.path.dirname(basedir)),
    "luthia-data", "luthia.db"
)}'

# Line 649
data_sources_dir = os.path.normpath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..', '..', 'data-sources'
    )
)
```

**Issues**:
- Double-nested `dirname()` calls are hard to parse
- `os.path.normpath()` can hide issues
- Mixed path construction styles

**Recommendation**: Centralize repo root calculation, use `pathlib.Path`

---

### 4. ✅ `import_species_csv.py`
**Input/Output Paths**: `data-sources/` subdirectories (lines 350, 357)

```python
# Line 42
SCRIPT_DIR = Path(__file__).parent.resolve()

# Lines 350, 357
default=SCRIPT_DIR / "data-sources" / "tonewood-species.csv"
default=SCRIPT_DIR / "data-sources" / "species.json"
```

**Status**: Already using `pathlib.Path`! ✅

**Minor Issue**: The paths assume `data-sources/` is a sibling of `scripts/`, but they're actually:
- Script location: `data-sources/scripts/import_species_csv.py`
- File location: `data-sources/tonewood-species.csv`

The default paths should be: `SCRIPT_DIR / ".." / "tonewood-species.csv"` (currently works only if run from the right place)

---

### 5. ⚠️ `migrate_images.py`
**Paths**:
- Database: `../../luthia-data/luthia.db` (line 14)
- Upload folder: `../../luthia-data/product-images/` (line 43)

```python
# Lines 13-14
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(
    os.path.dirname(os.path.dirname(basedir)),
    "luthia-data", "luthia.db"
)}'

# Line 43
upload_folder = os.path.join(
    os.path.dirname(os.path.dirname(basedir)),
    'luthia-data', 'product-images'
)
```

**Issues**: Same as `import_data.py` — fragile double-dirname pattern

---

### 6. ⚠️ `seed_templates.py`
**Path**: `../../luthia-data/luthia.db` (line 36)

```python
# Lines 35-36
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(
    os.path.dirname(os.path.dirname(basedir)),
    "luthia-data", "luthia.db"
)}'
```

**Issues**: Same as above — repeated fragile pattern across 3 files

---

## Repository Structure (Current)

```
Luthia-App/
├── data-sources/
│   ├── scripts/              ← Scripts location (was luthia-app/scripts/)
│   │   ├── create_github_project.py
│   │   ├── fret_calc_excel.py
│   │   ├── import_data.py
│   │   ├── import_species_csv.py
│   │   ├── migrate_images.py
│   │   └── seed_templates.py
│   └── *.xlsx              ← Vendor/species data files
├── luthia-data/             ← Database and output files
│   ├── luthia.db
│   └── product-images/
├── luthia-server/           ← Was luthia-app/
├── luthia-client/
├── docs/
└── ...
```

---

## Recommendations

### 1. **Standardize Path Resolution Pattern** (Priority: High)

Create a shared path utility to replace the fragile `dirname(dirname(...))` pattern:

```python
# In each script:
from pathlib import Path

# Get repo root: data-sources/scripts/ → data-sources/ → repo root
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent.parent

# Define paths from repo root
LUTHIA_DATA_DIR = REPO_ROOT / "luthia-data"
DATABASE_URL = f"sqlite:///{LUTHIA_DATA_DIR / 'luthia.db'}"
DATA_SOURCES_DIR = REPO_ROOT / "data-sources"
```

### 2. **Files Requiring Updates**

| File | Pattern | Lines | Recommendation |
|------|---------|-------|-----------------|
| `fret_calc_excel.py` | `../../luthia-data/` | 96 | Use `pathlib.Path` |
| `import_data.py` | `dirname(dirname(...))` | 13, 649 | Use `pathlib.Path` |
| `migrate_images.py` | `dirname(dirname(...))` | 14, 43 | Use `pathlib.Path` |
| `seed_templates.py` | `dirname(dirname(...))` | 36 | Use `pathlib.Path` |
| `import_species_csv.py` | `SCRIPT_DIR / "data-sources"` | 350, 357 | Fix path to parent directory |

### 3. **Benefits of Refactoring**

✅ **Clarity**: `REPO_ROOT / "luthia-data"` is self-documenting
✅ **Maintainability**: Single source of truth for paths
✅ **Flexibility**: Easy to run scripts from any directory
✅ **Robustness**: No magic dirname() nesting
✅ **Type Safety**: `pathlib.Path` objects with IDE autocompletion

---

## Next Steps

Would you like me to:

1. **Option A**: Update all 4 scripts to use the standardized `pathlib.Path` pattern
2. **Option B**: Create a shared `paths.py` utility module in `data-sources/scripts/`
3. **Option C**: Review specific path handling requirements before refactoring

**Estimated time**: Option A: ~15 min | Option B: ~20 min (includes shared module)
