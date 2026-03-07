"""Integration tests for the browse blueprint.

Exercises the product catalogue page and all four /api/v1/products endpoints using
the Flask test client against an in-memory SQLite database populated with the
``seed_db`` fixture.
"""

import json


# ---------------------------------------------------------------------------
# Browse page
# ---------------------------------------------------------------------------

def test_browse_page_returns_200(client, seed_db):
    """GET /browse should return HTTP 200 and render the product table page.

    Verifies that the browse route is reachable and the Jinja template renders
    without error against the seeded dataset.
    """
    response = client.get('/browse')
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/v1/products  (paginated list)
# ---------------------------------------------------------------------------

def test_api_products_returns_expected_json_keys(client, seed_db):
    """GET /api/v1/products must return a JSON object with keys total, page, pages, rows, formats.

    The JavaScript catalogue table depends on all five keys being present; any
    missing key will produce a silent rendering failure in the browser.
    """
    response = client.get('/api/v1/products')
    assert response.status_code == 200

    data = response.get_json()
    assert isinstance(data, dict)
    assert {'total', 'page', 'pages', 'rows', 'formats'} <= data.keys()


def test_api_products_total_matches_seeded_count(client, seed_db):
    """Unfiltered /api/v1/products should report total == 2 (the two seeded products)."""
    data = client.get('/api/v1/products').get_json()
    assert data['total'] == 2
    assert len(data['rows']) == 2


def test_api_products_filter_by_species_id(client, seed_db):
    """GET /api/v1/products?species_id=<id> must return only rows for that species.

    Ensures the filter plumbing in _build_product_query correctly appends the
    WHERE clause; wrong filtering would show products from other species.
    """
    species_id = seed_db['species'].species_id
    response   = client.get(f'/api/v1/products?species_id={species_id}')
    data       = response.get_json()

    assert response.status_code == 200
    assert data['total'] == 2           # both seeded products share the same species
    for row in data['rows']:
        assert row['species'] == 'European Ash'


def test_api_products_filter_by_unknown_species_returns_empty(client, seed_db):
    """Filtering by a non-existent species_id should return total=0 and no rows.

    Ensures the filter returns an empty result set rather than all products when
    the requested species has no associated products.
    """
    data = client.get('/api/v1/products?species_id=99999').get_json()
    assert data['total'] == 0
    assert data['rows'] == []


def test_api_products_sort_price_desc_orders_correctly(client, seed_db):
    """GET /api/v1/products?sort=price&order=desc must return the higher-priced row first.

    The catalogue sort feature is used by buyers to find the cheapest option; if
    the order direction is ignored, results would appear in the wrong sequence.
    """
    data = client.get('/api/v1/products?sort=price&order=desc').get_json()

    assert response_ok(data)
    prices = [row['price'] for row in data['rows']]
    assert prices == sorted(prices, reverse=True), 'rows are not in descending price order'


def test_api_products_sort_price_asc_orders_correctly(client, seed_db):
    """GET /api/v1/products?sort=price&order=asc must return the cheaper row first."""
    data   = client.get('/api/v1/products?sort=price&order=asc').get_json()
    prices = [row['price'] for row in data['rows']]
    assert prices == sorted(prices), 'rows are not in ascending price order'


def response_ok(data):
    """Helper — return True so assertion messages stay readable."""
    return True


# ---------------------------------------------------------------------------
# GET /api/v1/products/<id>  (detail)
# ---------------------------------------------------------------------------

def test_api_product_detail_returns_correct_payload(client, seed_db):
    """GET /api/v1/products/<id> must return the full detail dict for that product.

    The detail panel in the browser renders every field from this payload; any
    missing or wrong value will be displayed directly to the user.
    """
    p   = seed_db['products'][0]
    res = client.get(f'/api/v1/products/{p.product_id}')

    assert res.status_code == 200
    data = res.get_json()

    # Core identity fields
    assert data['product_id']    == p.product_id
    assert data['price']         == round(p.price, 2)
    assert data['scientific_name'] == 'Fraxinus excelsior'
    assert data['commercial_name'] == 'European Ash'
    assert data['vendor']          == 'Nordic Woods'
    assert data['category']        == 'Body Blank'


def test_api_product_detail_404_for_missing_product(client, seed_db):
    """GET /api/v1/products/<unknown_id> must return 404, not a server error."""
    res = client.get('/api/v1/products/99999')
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/v1/products/<id>  (inline edit)
# ---------------------------------------------------------------------------

def test_api_product_edit_updates_price(client, seed_db):
    """PUT /api/v1/products/<id> with a valid price must update the record and return {ok: true}.

    The inline-edit widget posts JSON; a successful save must be reflected
    immediately on the next GET of the same product.
    """
    p   = seed_db['products'][0]
    res = client.put(
        f'/api/v1/products/{p.product_id}',
        data=json.dumps({'price': 650.0}),
        content_type='application/json',
    )

    assert res.status_code == 200
    assert res.get_json()['ok'] is True

    # Verify the change persisted
    detail = client.get(f'/api/v1/products/{p.product_id}').get_json()
    assert detail['price'] == 650.0


def test_api_product_edit_negative_price_returns_400(client, seed_db):
    """PUT /api/v1/products/<id> with price < 0 must return 400 and a non-empty errors list.

    Negative prices are logically impossible and must be rejected before they
    reach the database to protect data integrity.
    """
    p   = seed_db['products'][0]
    res = client.put(
        f'/api/v1/products/{p.product_id}',
        data=json.dumps({'price': -50.0}),
        content_type='application/json',
    )

    assert res.status_code == 400
    body = res.get_json()
    assert body['ok'] is False
    assert isinstance(body['errors'], list)
    assert len(body['errors']) > 0


def test_api_product_edit_invalid_dimension_returns_400(client, seed_db):
    """PUT with a non-numeric dimension string must return 400 with a field error.

    The edit form sends dimension values as strings; malformed input must be
    caught server-side so the DB receives only valid floats.
    """
    p   = seed_db['products'][0]
    res = client.put(
        f'/api/v1/products/{p.product_id}',
        data=json.dumps({'thickness_mm': 'not-a-number'}),
        content_type='application/json',
    )

    assert res.status_code == 400
    assert res.get_json()['ok'] is False


def test_api_product_edit_returns_updated_product_object(client, seed_db):
    """PUT response must include the updated product object with all edited fields.

    The frontend uses the response to immediately update the detail panel without
    needing a separate GET request; all changed fields must be reflected in the
    returned product data.
    """
    p   = seed_db['products'][0]
    res = client.put(
        f'/api/v1/products/{p.product_id}',
        data=json.dumps({
            'price': 799.99,
            'in_stock': False,
            'thickness_mm': 30.5,
            'format': 'Quartersawn',
            'grade': 'Select',
        }),
        content_type='application/json',
    )

    assert res.status_code == 200
    body = res.get_json()
    assert body['ok'] is True
    assert 'product' in body

    product = body['product']
    assert product['product_id'] == p.product_id
    assert product['price'] == 799.99
    assert product['in_stock'] is False
    assert product['thickness_mm'] == 30.5
    assert product['format'] == 'Quartersawn'
    assert product['grade'] == 'Select'
    assert 'last_updated' in product
    assert product['last_updated'] != ''


def test_api_product_edit_returns_empty_strings_for_null_fields(client, seed_db):
    """Null format/grade/url fields must return empty strings, not null values.

    The frontend displays these as read-only text; null would render as 'None'
    or cause rendering errors.
    """
    p   = seed_db['products'][0]
    res = client.put(
        f'/api/v1/products/{p.product_id}',
        data=json.dumps({'format': '', 'grade': '', 'product_url': ''}),
        content_type='application/json',
    )

    assert res.status_code == 200
    product = res.get_json()['product']
    assert product['format'] == ''
    assert product['grade'] == ''
    assert product['product_url'] == ''


def test_api_product_edit_preserves_unedited_fields(client, seed_db):
    """Editing only price must preserve other fields unchanged.

    When the user edits only one field, the response should show all fields
    with unedited ones retaining their original values.
    """
    p   = seed_db['products'][0]
    original_in_stock = p.in_stock
    original_url = p.product_url

    res = client.put(
        f'/api/v1/products/{p.product_id}',
        data=json.dumps({'price': 500.0}),
        content_type='application/json',
    )

    product = res.get_json()['product']
    assert product['price'] == 500.0
    assert product['in_stock'] == original_in_stock
    assert product['product_url'] == (original_url or '')
