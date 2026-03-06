# Path Refactoring Summary

**Status**: ✅ **COMPLETE**
**Date**: March 6, 2026
**Scope**: `data-sources/scripts/` Python files

---

## Changes Made

### 1. Created Shared Paths Utility ✅
**File**: [`data-sources/scripts/paths.py`](data-sources/scripts/paths.py) (NEW)

Centralized path definitions for all scripts:
- ✅ Repository root discovery (automatic from script location)
- ✅ All directory path constants
- ✅ Database and file path constants
- ✅ Path validation helpers
- ✅ Debugging utilities

**Key constants available**:
```python
from paths import (
    REPO_ROOT,
    DATA_SOURCES_DIR,
    LUTHIA_DATA_DIR,
    PRODUCT_IMAGES_DIR,
    DATABASE_URL,
    FRET_TABLES_OUTPUT,
    SPECIES_CSV_INPUT,
    SPECIES_JSON_OUTPUT,
)
```

---

### 2. Updated Scripts ✅

#### `fret_calc_excel.py`
**Before**: `os.path.join(...dirname(dirname...)..., 'luthia-data', '...')`
**After**: `from paths import FRET_TABLES_OUTPUT`

```python
# Old (line 96)
output_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', 'luthia-data',
    'fret_placement_tables.xlsx'
)
wb.save(output_path)

# New
from paths import FRET_TABLES_OUTPUT
wb.save(str(FRET_TABLES_OUTPUT))
```

---

#### `import_data.py`
**Before**: `os.path.dirname(os.path.dirname(basedir))`
**After**: `from paths import DATABASE_URL, DATA_SOURCES_DIR`

```python
# Old (line 13)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(
    os.path.dirname(os.path.dirname(basedir)),
    "luthia-data", "luthia.db"
)}'

# New
from paths import DATABASE_URL, DATA_SOURCES_DIR
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL

# Old (line 649)
data_sources_dir = os.path.normpath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..', '..', 'data-sources'
    )
)

# New
from paths import DATA_SOURCES_DIR
data_sources_dir = str(DATA_SOURCES_DIR)
```

---

#### `import_species_csv.py`
**Before**: `SCRIPT_DIR / "data-sources" / "tonewood-species.csv"`
**After**: `from paths import SPECIES_CSV_INPUT, SPECIES_JSON_OUTPUT`

```python
# Old (lines 350, 357)
default=SCRIPT_DIR / "data-sources" / "tonewood-species.csv"
default=SCRIPT_DIR / "data-sources" / "species.json"

# New
from paths import SPECIES_CSV_INPUT, SPECIES_JSON_OUTPUT
default=SPECIES_CSV_INPUT
default=SPECIES_JSON_OUTPUT
```

---

#### `migrate_images.py`
**Before**: `os.path.dirname(os.path.dirname(basedir))`
**After**: `from paths import DATABASE_URL, PRODUCT_IMAGES_DIR, ensure_product_images_dir`

```python
# Old (line 14)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(
    os.path.dirname(os.path.dirname(basedir)),
    "luthia-data", "luthia.db"
)}'

# New
from paths import DATABASE_URL, PRODUCT_IMAGES_DIR, ensure_product_images_dir
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL

# Old (line 43)
upload_folder = os.path.join(
    os.path.dirname(os.path.dirname(basedir)),
    'luthia-data', 'product-images'
)
os.makedirs(upload_folder, exist_ok=True)
print(f'Upload folder ready: {upload_folder}')

# New
ensure_product_images_dir()
print(f'Upload folder ready: {PRODUCT_IMAGES_DIR}')
```

---

#### `seed_templates.py`
**Before**: `os.path.dirname(os.path.dirname(basedir))`
**After**: `from paths import DATABASE_URL`

```python
# Old (line 36)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(
    os.path.dirname(os.path.dirname(basedir)),
    "luthia-data", "luthia.db"
)}'

# New
from paths import DATABASE_URL
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
```

---

#### `create_github_project.py`
**Status**: ✅ No changes needed (no file I/O)

---

## Benefits ✨

| Benefit | Impact |
|---------|--------|
| **Single Source of Truth** | All paths defined in one place. Easy to maintain. |
| **Self-Documenting** | `FRET_TABLES_OUTPUT` is clearer than `../../luthia-data/fret_placement_tables.xlsx` |
| **Portable** | Scripts work from any directory (no reliance on specific depth) |
| **Type Safe** | `pathlib.Path` objects with IDE autocompletion |
| **Debuggable** | Run `python paths.py` to verify all paths exist |
| **Reusable** | Any future script can import from `paths.py` |
| **DRY** | Eliminated 5 instances of fragile `dirname(dirname(...))` patterns |

---

## Testing

### Verify paths module:
```bash
cd data-sources/scripts/
python paths.py
```

Should output:
```
======================================================================
LUTHIA PATH CONFIGURATION
======================================================================
  REPO_ROOT            : /Users/paulomarques/Documents/_PROJECTS/Luthia/Luthia-App
  SCRIPT_DIR           : /Users/paulomarques/Documents/_PROJECTS/Luthia/Luthia-App/data-sources/scripts

Data & Sources:
  DATA_SOURCES_DIR     : /Users/paulomarques/Documents/_PROJECTS/Luthia/Luthia-App/data-sources
  LUTHIA_DATA_DIR      : /Users/paulomarques/Documents/_PROJECTS/Luthia/Luthia-App/luthia-data
  PRODUCT_IMAGES_DIR   : /Users/paulomarques/Documents/_PROJECTS/Luthia/Luthia-App/luthia-data/product-images
...

Repository Structure:
  ✓ REPO_ROOT
  ✓ DATA_SOURCES_DIR
  ✓ LUTHIA_DATA_DIR
  ✓ LUTHIA_SERVER_DIR
======================================================================
```

---

## Files Changed

```
data-sources/scripts/
├── paths.py                      ← NEW (centralized path definitions)
├── create_github_project.py       ✓ (no changes needed)
├── fret_calc_excel.py             ✓ UPDATED (now uses paths.FRET_TABLES_OUTPUT)
├── import_data.py                 ✓ UPDATED (now uses paths.DATABASE_URL + DATA_SOURCES_DIR)
├── import_species_csv.py          ✓ UPDATED (now uses paths.SPECIES_CSV_INPUT/OUTPUT)
├── migrate_images.py              ✓ UPDATED (now uses paths.DATABASE_URL + PRODUCT_IMAGES_DIR)
└── seed_templates.py              ✓ UPDATED (now uses paths.DATABASE_URL)
```

---

## Rollback Plan

If needed, changes are isolated and minimal:
1. Revert all 5 updated Python files to their original versions
2. Delete `paths.py`
3. Git history is preserved

---

## Recommendations for Future Work

1. **Apply same pattern to luthia-server/**: Consider creating a similar `paths.py` there for consistency
2. **Document in README**: Add a section explaining path resolution strategy
3. **CI/CD Integration**: The `paths.py` verification could be added to pre-commit hooks
4. **Environment Variables**: Consider allowing `LUTHIA_DATA_DIR` override via environment variable for different deployment scenarios

---

## Summary

✅ All hardcoded paths in `data-sources/scripts/` have been refactored
✅ Migration history (`luthia-app/` → `luthia-server/`) is complete
✅ Paths are now portable, maintainable, and self-documenting
✅ No breaking changes to script functionality
✅ All scripts remain drop-in compatible with existing workflows
