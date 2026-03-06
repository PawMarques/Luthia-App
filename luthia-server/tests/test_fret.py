"""Unit and integration tests for the fret calculator blueprint.

Covers _compute_frets() pure-Python logic and every HTTP endpoint defined in
routes/fret.py.  The pure-Python unit tests require no fixtures; the HTTP tests
need only the ``client`` fixture because the fret routes never touch the database.
"""

import math

from routes.fret import _compute_frets


# ---------------------------------------------------------------------------
# _compute_frets — pure-Python unit tests  (no HTTP, no DB, no fixtures)
# ---------------------------------------------------------------------------

def test_compute_frets_fret_0_is_at_nut():
    """Fret 0 represents the nut: its distance from the nut must be exactly 0 mm."""
    frets = _compute_frets(863.6, 24)
    assert frets[0]['fret'] == 0
    assert frets[0]['from_nut_mm'] == 0.0


def test_compute_frets_fret_12_is_half_scale():
    """Fret 12 must fall at exactly scale_length / 2 (the octave node).

    Equal temperament places every 12th fret at the midpoint of the remaining
    string length.  For a 34″ bass (863.6 mm) that is 431.8 mm from the nut.
    """
    frets = _compute_frets(863.6, 24)
    expected = 863.6 / 2  # 431.8
    assert abs(frets[12]['from_nut_mm'] - expected) < 0.1


def test_compute_frets_spacing_decreases_monotonically():
    """Each successive fret spacing must be strictly smaller than the previous.

    Equal temperament compresses fret spacings towards the body; any spacing
    that is >= the one before it indicates a calculation error.
    """
    frets = _compute_frets(863.6, 24)
    spacings = [f['spacing_mm'] for f in frets if f['spacing_mm'] is not None]
    for i in range(1, len(spacings)):
        assert spacings[i] < spacings[i - 1], (
            f'spacing at fret {i + 1} ({spacings[i]:.4f} mm) is not less than '
            f'spacing at fret {i} ({spacings[i - 1]:.4f} mm)'
        )


def test_compute_frets_returns_correct_entry_count():
    """_compute_frets(scale, 24) must return 25 entries: frets 0 through 24."""
    frets = _compute_frets(863.6, 24)
    assert len(frets) == 25


# ---------------------------------------------------------------------------
# GET /api/v1/fret/calculate
# ---------------------------------------------------------------------------

def test_api_fret_calculate_valid_returns_200_and_ok(client):
    """A well-formed request must return HTTP 200 with ok=True in the payload."""
    response = client.get('/api/v1/fret/calculate?scale_mm=863.6&num_frets=24')
    assert response.status_code == 200
    data = response.get_json()
    assert data['ok'] is True


def test_api_fret_calculate_returns_25_fret_entries(client):
    """num_frets=24 must produce a 'frets' list with exactly 25 entries (0–24).

    Fret 0 is the nut; the list always has num_frets + 1 items.
    """
    data = client.get('/api/v1/fret/calculate?scale_mm=863.6&num_frets=24').get_json()
    assert len(data['frets']) == 25
    assert data['frets'][0]['fret'] == 0
    assert data['frets'][24]['fret'] == 24


def test_api_fret_calculate_missing_scale_mm_returns_400(client):
    """Omitting the required scale_mm parameter must return 400 with ok=False."""
    response = client.get('/api/v1/fret/calculate?num_frets=24')
    assert response.status_code == 400
    assert response.get_json()['ok'] is False


def test_api_fret_calculate_negative_scale_mm_returns_400(client):
    """A negative scale_mm value is physically meaningless and must return 400."""
    response = client.get('/api/v1/fret/calculate?scale_mm=-100')
    assert response.status_code == 400
    assert response.get_json()['ok'] is False


def test_api_fret_calculate_num_frets_99_returns_400(client):
    """num_frets=99 exceeds the maximum of 36 and must be rejected with 400."""
    response = client.get('/api/v1/fret/calculate?scale_mm=863.6&num_frets=99')
    assert response.status_code == 400
    assert response.get_json()['ok'] is False


# ---------------------------------------------------------------------------
# GET /api/v1/fret/export
# ---------------------------------------------------------------------------

def test_api_fret_export_returns_xlsx(client):
    """GET /api/v1/fret/export must return HTTP 200 with an xlsx MIME type.

    The response must carry the OpenXML spreadsheet content-type so that the
    browser triggers a download rather than attempting to render the bytes.
    """
    response = client.get('/api/v1/fret/export?scale_mm=863.6')
    assert response.status_code == 200
    assert 'spreadsheetml.sheet' in response.content_type
