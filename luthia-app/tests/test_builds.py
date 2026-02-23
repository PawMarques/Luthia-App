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
    """POST /builds/new with complete form data must create a Build row and return a JS redirect.

    The route returns a 200 with a <script>window.location=...></script> body
    rather than an HTTP redirect; the test asserts that the build was persisted
    and that the response body points to the new build's URL.
    """
    template = seed_db['template']
    variant  = seed_db['variant']

    response = client.post('/builds/new', data={
        'template_id': template.template_id,
        'variant_id':  variant.variant_id,
        'name':        'Integration Test Build',
    })

    assert response.status_code == 200
    # The route embeds a JS redirect pointing to /builds/<new_id>
    assert b'/builds/' in response.data

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
    # A JS redirect would include '/builds/<id>'; the raw form HTML won't
    assert b'window.location="/builds/' not in response.data

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
    """GET /api/builds/<id>/candidates/body must return a JSON array.

    The picker modal populates itself from this endpoint; a non-array or empty
    response would leave the user unable to select a body blank.
    """
    build_id = seed_db['build'].build_id
    response = client.get(f'/api/builds/{build_id}/candidates/body')

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)


def test_api_candidates_body_contains_seeded_products(client, seed_db):
    """The body candidates list must include the two seeded Body Blank products.

    Both products (500 × 400 × 50 mm) exceed the variant's minimum dimensions
    (480 × 350 × 45 mm), so neither should be filtered out.
    """
    build_id = seed_db['build'].build_id
    data     = client.get(f'/api/builds/{build_id}/candidates/body').get_json()

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
    data     = client.get(f'/api/builds/{build_id}/candidates/unknown_role').get_json()

    assert isinstance(data, list)
    assert data == []


# ---------------------------------------------------------------------------
# Part assignment (PATCH)
# ---------------------------------------------------------------------------

def test_api_build_part_update_assigns_product(client, seed_db):
    """PATCH /api/builds/<id>/parts/<part_id> must assign a product and return {ok: true}.

    The picker sends this request when the user picks a product; a failure here
    means the selection is never persisted to the database.
    """
    build   = seed_db['build']
    part    = seed_db['part']
    product = seed_db['products'][0]

    response = client.patch(
        f'/api/builds/{build.build_id}/parts/{part.part_id}',
        data=json.dumps({'product_id': product.product_id}),
        content_type='application/json',
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body['ok'] is True

    # The response should also include the recomputed total price
    assert 'total' in body


# ---------------------------------------------------------------------------
# Build deletion (DELETE)
# ---------------------------------------------------------------------------

def test_api_build_delete_removes_build(client, seed_db):
    """DELETE /api/builds/<id> must delete the build row and return {ok: true}.

    After deletion the build should not be retrievable; a subsequent GET must
    return 404 to confirm the record is gone from the database.
    """
    build_id = seed_db['build'].build_id

    response = client.delete(f'/api/builds/{build_id}')

    assert response.status_code == 200
    assert response.get_json()['ok'] is True

    # Confirm the build is no longer in the database
    from models import db as _db
    assert _db.session.get(Build, build_id) is None


def test_api_build_delete_404_for_unknown_build(client, db_session):
    """DELETE /api/builds/<unknown_id> must return 404, not a 500."""
    response = client.delete('/api/builds/99999')
    assert response.status_code == 404
