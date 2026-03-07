"""Integration tests for the builds blueprint.

Exercises the build planner HTML pages and JSON API endpoints using the Flask
test client against an in-memory SQLite database.  The ``seed_db`` fixture
provides one template + variant + build + part so every route has the data it
needs to render without additional HTTP-level setup.
"""

import json

from models import Build, db


# ---------------------------------------------------------------------------
# HTML page routes
# ---------------------------------------------------------------------------

def test_builds_index_returns_200(client, seed_db):
    """GET /builds must return HTTP 200 and render the build planner index page.

    If the page fails to render (e.g. a broken template or missing ORM query)
    the user would see a 500 error instead of their build list.
    """
    response = client.get('/builds')
    assert response.status_code == 200


def test_builds_new_get_returns_200(client, seed_db):
    """GET /builds/new must return HTTP 200 with the new-build form.

    The form must be reachable so users can start a new build from the planner.
    """
    response = client.get('/builds/new')
    assert response.status_code == 200


def test_builds_new_post_valid_creates_build_and_responds(client, seed_db):
    """POST /builds/new with complete form data must create a Build row and redirect to it.

    The route returns a 302 HTTP redirect to /builds/<new_id>; the test asserts
    that the build was persisted and that the Location header points to the new
    build's URL.
    """
    template = seed_db['template']
    variant  = seed_db['variant']

    response = client.post('/builds/new', data={
        'template_id': template.template_id,
        'variant_id':  variant.variant_id,
        'name':        'Integration Test Build',
    })

    assert response.status_code == 302
    # The Location header must point to /builds/<new_id>
    assert b'/builds/' in response.headers['Location'].encode()

    # A new Build row must exist in the database
    builds = Build.query.filter_by(name='Integration Test Build').all()
    assert len(builds) == 1


def test_builds_new_post_missing_name_returns_form(client, db_session):
    """POST /builds/new with empty name must return the form (200), not create a Build.

    The route sets an error variable internally and re-renders builds/new.html.
    The template does not currently have an error display block, so we assert
    behavioural correctness at the HTTP level: a 200 response means the form
    was re-rendered rather than redirecting to a new build, and we confirm no
    Build row was persisted to the database.
    """
    response = client.post('/builds/new', data={
        'template_id': 1,
        'variant_id':  1,
        'name':        '',   # deliberately blank
    })

    assert response.status_code == 200
    # A successful redirect would be 302; re-rendered form stays at 200
    assert response.status_code != 302

    # No Build row should have been written
    from models import Build
    assert Build.query.count() == 0


def test_builds_detail_returns_200(client, seed_db):
    """GET /builds/<id> must return HTTP 200 for an existing seeded build.

    Verifies that the detail page fetches the build, its variant dimensions,
    and all part rows without raising any template or ORM errors.
    """
    build_id = seed_db['build'].build_id
    response = client.get(f'/builds/{build_id}')
    assert response.status_code == 200


def test_builds_detail_404_for_unknown_id(client, db_session):
    """GET /builds/<unknown_id> must return 404, not a 500 server error."""
    response = client.get('/builds/99999')
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Candidates API
# ---------------------------------------------------------------------------

def test_api_candidates_body_returns_json_array(client, seed_db):
    """GET /api/v1/builds/<id>/candidates/body must return a JSON array.

    The picker modal populates itself from this endpoint; a non-array or empty
    response would leave the user unable to select a body blank.
    """
    build_id = seed_db['build'].build_id
    response = client.get(f'/api/v1/builds/{build_id}/candidates/body')

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)


def test_api_candidates_body_contains_seeded_products(client, seed_db):
    """The body candidates list must include the two seeded Body Blank products.

    Both products (500 × 400 × 50 mm) exceed the variant's minimum dimensions
    (480 × 350 × 45 mm), so neither should be filtered out.
    """
    build_id = seed_db['build'].build_id
    data     = client.get(f'/api/v1/builds/{build_id}/candidates/body').get_json()

    assert len(data) == 2
    ids = {row['id'] for row in data}
    expected = {p.product_id for p in seed_db['products']}
    assert ids == expected


def test_api_candidates_unknown_role_returns_empty_array(client, seed_db):
    """A non-existent role name must return an empty JSON array, not a 404 or 500.

    The candidates helper returns [] when the role isn't in ROLE_CATEGORIES,
    so the picker can handle unknown roles gracefully.
    """
    build_id = seed_db['build'].build_id
    data     = client.get(f'/api/v1/builds/{build_id}/candidates/unknown_role').get_json()

    assert isinstance(data, list)
    assert data == []


# ---------------------------------------------------------------------------
# Part assignment (PATCH)
# ---------------------------------------------------------------------------

def test_api_build_part_update_assigns_product(client, seed_db):
    """PATCH /api/v1/builds/<id>/parts/<part_id> must assign a product and return {ok: true}.

    The picker sends this request when the user picks a product; a failure here
    means the selection is never persisted to the database.
    """
    build   = seed_db['build']
    part    = seed_db['part']
    product = seed_db['products'][0]

    response = client.patch(
        f'/api/v1/builds/{build.build_id}/parts/{part.part_id}',
        data=json.dumps({'product_id': product.product_id}),
        content_type='application/json',
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body['ok'] is True

    # The response should also include the recomputed total price
    assert 'total' in body


def test_api_build_part_update_returns_part_object(client, seed_db):
    """PATCH response must include the updated part object with all state flags.

    The frontend uses the response to update the part UI without needing a
    separate fetch; dims_unverified and thickness_warning flags control
    display warnings in the build planner.
    """
    build   = seed_db['build']
    part    = seed_db['part']
    product = seed_db['products'][0]

    response = client.patch(
        f'/api/v1/builds/{build.build_id}/parts/{part.part_id}',
        data=json.dumps({'product_id': product.product_id}),
        content_type='application/json',
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body['ok'] is True
    assert 'part' in body
    assert 'total' in body

    part_data = body['part']
    assert part_data['part_id'] == part.part_id
    assert part_data['role'] == part.role
    assert part_data['product_id'] == product.product_id
    assert isinstance(part_data['dims_unverified'], bool)
    assert isinstance(part_data['thickness_warning'], bool)


def test_api_build_part_update_dims_unverified_flag_with_complete_product(client, seed_db):
    """PATCH should set dims_unverified=false when product has all dimension data.

    When a product has length, width, and thickness recorded, the builder can
    rely on the dimensional checks and the flag should be false.
    """
    build   = seed_db['build']
    part    = seed_db['part']
    product = seed_db['products'][0]  # Seeded products have complete dimensions

    response = client.patch(
        f'/api/v1/builds/{build.build_id}/parts/{part.part_id}',
        data=json.dumps({'product_id': product.product_id}),
        content_type='application/json',
    )

    part_data = response.get_json()['part']
    assert part_data['dims_unverified'] is False


def test_api_build_part_update_clears_product_assignment(client, seed_db):
    """PATCH with product_id=null should clear the product assignment.

    The picker can be used to clear a part selection; dims_unverified should
    be reset to false when no product is assigned.
    """
    build   = seed_db['build']
    part    = seed_db['part']
    product = seed_db['products'][0]

    # First assign a product
    client.patch(
        f'/api/v1/builds/{build.build_id}/parts/{part.part_id}',
        data=json.dumps({'product_id': product.product_id}),
        content_type='application/json',
    )

    # Now clear it
    response = client.patch(
        f'/api/v1/builds/{build.build_id}/parts/{part.part_id}',
        data=json.dumps({'product_id': None}),
        content_type='application/json',
    )

    part_data = response.get_json()['part']
    assert part_data['product_id'] is None
    assert part_data['dims_unverified'] is False


# ---------------------------------------------------------------------------
# Build deletion (DELETE)
# ---------------------------------------------------------------------------

def test_api_build_delete_removes_build(client, seed_db):
    """DELETE /api/v1/builds/<id> must delete the build row and return {ok: true}.

    After deletion the build should not be retrievable; a subsequent GET must
    return 404 to confirm the record is gone from the database.
    """
    build_id = seed_db['build'].build_id

    response = client.delete(f'/api/v1/builds/{build_id}')

    assert response.status_code == 200
    assert response.get_json()['ok'] is True

    # Confirm the build is no longer in the database
    from models import db as _db
    assert _db.session.get(Build, build_id) is None


def test_api_build_delete_404_for_unknown_build(client, db_session):
    """DELETE /api/v1/builds/<unknown_id> must return 404, not a 500."""
    response = client.delete('/api/v1/builds/99999')
    assert response.status_code == 404
