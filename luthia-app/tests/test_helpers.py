"""Unit tests for helpers.py.

All functions in helpers.py are pure (no Flask / SQLAlchemy imports), so
these tests run without any application context or database.
"""

import pytest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from helpers import allowed_file, fmt_dims, fmt_image, staleness_color, staleness_info


# ---------------------------------------------------------------------------
# allowed_file
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('filename,expected', [
    # Valid extensions — each member of ALLOWED_EXTENSIONS
    ('photo.jpg',  True),
    ('photo.jpeg', True),
    ('photo.png',  True),
    ('photo.webp', True),
    ('photo.gif',  True),
    # Case-insensitive matching
    ('photo.JPG',  True),
    ('photo.PNG',  True),
    # Invalid / unrecognised extensions
    ('photo.bmp',  False),
    ('photo.tiff', False),
    ('photo.pdf',  False),
    ('photo.svg',  False),
    # Edge cases
    ('photo',      False),  # no extension at all
    ('',           False),  # empty string — no dot, must return False
    ('.hidden',    False),  # dot-file with no real extension (rsplit gives ['', 'hidden'])
])
def test_allowed_file(filename, expected):
    """Verify that allowed_file accepts exactly the five approved image extensions.

    Matters because the image upload route relies on this guard to prevent
    arbitrary file types from reaching the upload directory.
    """
    assert allowed_file(filename) is expected


# ---------------------------------------------------------------------------
# staleness_color — boundary tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('age_months,expected', [
    (0.0,  '#34d399'),   # brand-new — green
    (3.0,  '#34d399'),   # exactly 3 months — still green (≤ 3 boundary)
    (3.01, '#f59e0b'),   # just past 3 months — amber
    (6.0,  '#f59e0b'),   # exactly 6 months — amber (≤ 6 boundary)
    (6.01, '#f87171'),   # just past 6 months — red
    (12.0, '#f87171'),   # one year — firmly red
])
def test_staleness_color(age_months, expected):
    """Verify the three-bucket colour boundaries: green ≤3, amber ≤6, red >6.

    The browse table uses these colours to give buyers a quick visual signal
    about how fresh a price entry is; wrong boundaries would mislead users.
    """
    assert staleness_color(age_months) == expected


# ---------------------------------------------------------------------------
# staleness_info
# ---------------------------------------------------------------------------

def test_staleness_info_none_returns_empty_and_muted_grey():
    """staleness_info(None) must return ('', muted grey) without raising.

    Route code calls staleness_info without checking for None first, so a None
    input must be handled gracefully inside the function.
    """
    date_str, color = staleness_info(None)
    assert date_str == ''
    assert color == '#3f3f46'


def test_staleness_info_one_month_ago_is_green():
    """A date ~1 month ago should return the formatted date string and green colour.

    The mock pins datetime.utcnow so the age calculation is deterministic even
    when the test suite runs at any future point in time.
    """
    fixed_now     = datetime(2026, 2, 23)
    one_month_ago = datetime(2026, 1, 23)

    with patch('helpers.datetime') as mock_dt:
        mock_dt.now.return_value.replace.return_value = fixed_now
        date_str, color = staleness_info(one_month_ago)

    assert date_str == '2026-01-23'
    assert color == '#34d399'


def test_staleness_info_five_months_ago_is_amber():
    """A date ~5 months ago should return amber; price data is getting stale."""
    fixed_now        = datetime(2026, 2, 23)
    five_months_ago  = datetime(2025, 9, 23)

    with patch('helpers.datetime') as mock_dt:
        mock_dt.now.return_value.replace.return_value = fixed_now
        date_str, color = staleness_info(five_months_ago)

    assert date_str == '2025-09-23'
    assert color == '#f59e0b'


def test_staleness_info_eight_months_ago_is_red():
    """A date ~8 months ago should return red; price should be reverified."""
    fixed_now        = datetime(2026, 2, 23)
    eight_months_ago = datetime(2025, 6, 23)

    with patch('helpers.datetime') as mock_dt:
        mock_dt.now.return_value.replace.return_value = fixed_now
        date_str, color = staleness_info(eight_months_ago)

    assert date_str == '2025-06-23'
    assert color == '#f87171'


# ---------------------------------------------------------------------------
# fmt_dims
# ---------------------------------------------------------------------------

def _product(thickness=None, width=None, length=None):
    """Helper — return a SimpleNamespace mimicking the Product ORM attributes."""
    return SimpleNamespace(thickness_mm=thickness, width_mm=width, length_mm=length)


def test_fmt_dims_all_three_dimensions():
    """All three dimensions present — result is 'T × W × L mm'."""
    assert fmt_dims(_product(50, 400, 500)) == '50 × 400 × 500 mm'


def test_fmt_dims_two_dimensions():
    """Only thickness and width set — result omits the missing length."""
    assert fmt_dims(_product(thickness=50, width=400)) == '50 × 400 mm'


def test_fmt_dims_one_dimension():
    """Only thickness set — no separators, but still appends ' mm'."""
    assert fmt_dims(_product(thickness=45)) == '45 mm'


def test_fmt_dims_no_dimensions_returns_empty_string():
    """No dimensions on record — returns empty string so callers need no guard."""
    assert fmt_dims(_product()) == ''


def test_fmt_dims_skips_falsy_zero():
    """A zero value is falsy in Python and should be treated as 'not set'."""
    # 0.0 is falsy, so it should be skipped just like None.
    assert fmt_dims(_product(thickness=0.0, width=400, length=500)) == '400 × 500 mm'


# ---------------------------------------------------------------------------
# fmt_image
# ---------------------------------------------------------------------------

def _image(**kwargs):
    """Helper — return a SimpleNamespace mimicking a ProductImage ORM object."""
    defaults = dict(
        image_id=1,
        source_type='upload',
        filename='1_abc123.jpg',
        url=None,
        caption='Test caption',
        sort_order=0,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_fmt_image_upload_builds_static_path():
    """An 'upload' image must produce a /uploads/<filename> src URL.

    The browse panel builds <img src="..."> tags directly from this value, so
    the path must be rooted at /uploads/.
    """
    img    = _image(source_type='upload', filename='42_deadbeef.jpg')
    result = fmt_image(img)

    assert result['src'] == '/uploads/42_deadbeef.jpg'
    assert result['source_type'] == 'upload'
    assert result['image_id'] == 1


def test_fmt_image_url_passes_through_the_url():
    """A 'url' image must use the stored URL directly as its src.

    External URL images aren't saved locally, so the src must be the raw URL.
    """
    img    = _image(source_type='url', url='https://example.com/wood.jpg', filename=None)
    result = fmt_image(img)

    assert result['src'] == 'https://example.com/wood.jpg'
    assert result['source_type'] == 'url'


def test_fmt_image_url_with_null_url_returns_empty_src():
    """A 'url' image whose url column is NULL should yield an empty src string."""
    img    = _image(source_type='url', url=None, filename=None)
    result = fmt_image(img)

    assert result['src'] == ''


def test_fmt_image_caption_none_returns_empty_string():
    """A NULL caption column must be serialised as '' not None."""
    img    = _image(caption=None)
    result = fmt_image(img)

    assert result['caption'] == ''


def test_fmt_image_includes_all_required_keys():
    """Every dict returned by fmt_image must carry the five keys the JS panel expects."""
    result = fmt_image(_image())
    assert {'image_id', 'source_type', 'src', 'caption', 'sort_order'} <= result.keys()
