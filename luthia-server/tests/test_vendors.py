"""Integration tests for the vendors blueprint.

Exercises GET / POST / PATCH / DELETE on /api/v1/vendors using the Flask test
client against an in-memory SQLite database.  All tests use the ``seed_db``
fixture which provides one vendor: Nordic Woods (Sweden, SEK, active=True).
"""

import json


# ---------------------------------------------------------------------------
# GET /api/v1/vendors  (list)
# ---------------------------------------------------------------------------

def test_api_vendors_returns_200_with_nordic_woods(client, seed_db):
    """GET /api/v1/vendors must return HTTP 200 and include 'Nordic Woods' from seed data.

    The vendor management page uses this endpoint to populate its table;
    if the seeded vendor is absent the page would render an empty list.
    """
    response = client.get('/api/v1/vendors')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    names = [v['name'] for v in data]
    assert 'Nordic Woods' in names


# ---------------------------------------------------------------------------
# POST /api/v1/vendors  (create)
# ---------------------------------------------------------------------------

def test_api_vendor_create_valid_returns_201(client, seed_db):
    """POST /api/v1/vendors with a valid payload must create the record and return 201.

    The response must contain ok=True and the new vendor dict so the UI can
    immediately display the new row without a round-trip GET.
    """
    payload = {'name': 'Tonewood Sweden', 'country': 'Sweden', 'currency': 'SEK'}
    response = client.post(
        '/api/v1/vendors',
        data=json.dumps(payload),
        content_type='application/json',
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data['ok'] is True
    assert 'vendor' in data
    assert data['vendor']['name'] == 'Tonewood Sweden'


def test_api_vendor_create_duplicate_name_returns_400(client, seed_db):
    """POST /api/v1/vendors with the existing name 'Nordic Woods' must return 400.

    The uniqueness constraint prevents duplicate entries; the response must
    include a non-empty errors list explaining the rejection.
    """
    response = client.post(
        '/api/v1/vendors',
        data=json.dumps({'name': 'Nordic Woods'}),
        content_type='application/json',
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data['ok'] is False
    assert isinstance(data['errors'], list)
    assert len(data['errors']) > 0


def test_api_vendor_create_empty_name_returns_400(client, seed_db):
    """POST /api/v1/vendors with an empty name must return 400 with a validation error.

    An empty name is logically invalid; accepting it would create an unusable
    vendor record in the database.
    """
    response = client.post(
        '/api/v1/vendors',
        data=json.dumps({'name': ''}),
        content_type='application/json',
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data['ok'] is False
    assert isinstance(data['errors'], list)
    assert len(data['errors']) > 0


# ---------------------------------------------------------------------------
# PATCH /api/v1/vendors/<id>  (update)
# ---------------------------------------------------------------------------

def test_api_vendor_update_country(client, seed_db):
    """PATCH /api/v1/vendors/<id> with a new country must update the field and return ok=True.

    The response must echo back the updated vendor dict so the UI can refresh
    the row without a separate GET.
    """
    vendor_id = seed_db['vendor'].vendor_id
    response = client.patch(
        f'/api/v1/vendors/{vendor_id}',
        data=json.dumps({'country': 'Norway'}),
        content_type='application/json',
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data['ok'] is True
    assert data['vendor']['country'] == 'Norway'


# ---------------------------------------------------------------------------
# DELETE /api/v1/vendors/<id>  (soft-delete / toggle)
# ---------------------------------------------------------------------------

def test_api_vendor_toggle_active_twice(client, seed_db):
    """DELETE /api/v1/vendors/<id> must toggle the active flag on each call.

    The seed vendor starts with active=True.  The first DELETE flips it to
    False; a second DELETE restores it to True.  This verifies both the
    deactivation and the reactivation paths through the same endpoint.
    """
    vendor_id = seed_db['vendor'].vendor_id

    # First toggle: True → False
    r1 = client.delete(f'/api/v1/vendors/{vendor_id}')
    assert r1.status_code == 200
    d1 = r1.get_json()
    assert d1['ok'] is True
    assert d1['vendor']['active'] is False

    # Second toggle: False → True
    r2 = client.delete(f'/api/v1/vendors/{vendor_id}')
    assert r2.status_code == 200
    d2 = r2.get_json()
    assert d2['ok'] is True
    assert d2['vendor']['active'] is True
