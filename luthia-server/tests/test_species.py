"""Integration tests for the species blueprint.

Exercises /api/v1/species (list + search + filters) and /api/v1/species/<id> (detail)
using the Flask test client against an in-memory SQLite database.  All tests
use the ``seed_db`` fixture which provides one species (European Ash /
Fraxinus excelsior) with cites_listed unset (defaults to False).
"""


# ---------------------------------------------------------------------------
# GET /api/v1/species  (list)
# ---------------------------------------------------------------------------

def test_api_species_list_returns_200_with_required_keys(client, seed_db):
    """GET /api/v1/species must return HTTP 200 with at least 'rows' and 'total' keys.

    The JavaScript species grid depends on these keys; a missing key would
    produce a silent rendering failure in the browser.
    """
    response = client.get('/api/v1/species')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    assert 'rows' in data
    assert 'total' in data


def test_api_species_list_includes_seeded_species(client, seed_db):
    """Unfiltered /api/v1/species must include the seeded European Ash species."""
    data = client.get('/api/v1/species').get_json()
    assert data['total'] >= 1
    commercial_names = [row['commercial_name'] for row in data['rows']]
    assert 'European Ash' in commercial_names


def test_api_species_search_ash_returns_european_ash(client, seed_db):
    """GET /api/v1/species?q=ash must match 'European Ash' via commercial_name search.

    The search is a case-insensitive LIKE filter across multiple name columns;
    the seed species must appear in the results.
    """
    response = client.get('/api/v1/species?q=ash')
    assert response.status_code == 200
    data = response.get_json()
    assert data['total'] >= 1
    names = [row['commercial_name'] for row in data['rows']]
    assert 'European Ash' in names


def test_api_species_search_no_match_returns_empty(client, seed_db):
    """A search string that matches nothing must return total=0 and an empty rows list."""
    response = client.get('/api/v1/species?q=zzznomatch')
    assert response.status_code == 200
    data = response.get_json()
    assert data['total'] == 0
    assert data['rows'] == []


def test_api_species_cites_filter_returns_zero_for_seed_data(client, seed_db):
    """GET /api/v1/species?cites=1 must return total=0 because the seed species is
    not CITES-listed (cites_listed is False by default).

    This verifies the filter is applied correctly rather than being silently
    ignored.
    """
    response = client.get('/api/v1/species?cites=1')
    assert response.status_code == 200
    data = response.get_json()
    assert data['total'] == 0


# ---------------------------------------------------------------------------
# GET /api/v1/species/<id>  (detail)
# ---------------------------------------------------------------------------

def test_api_species_detail_returns_200_with_scientific_name(client, seed_db):
    """GET /api/v1/species/<valid_id> must return 200 and a payload containing
    the scientific_name field with the correct value.

    The detail modal renders scientific_name prominently; a wrong or missing
    value would be shown directly to users.
    """
    species_id = seed_db['species'].species_id
    response = client.get(f'/api/v1/species/{species_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert 'scientific_name' in data
    assert data['scientific_name'] == 'Fraxinus excelsior'


def test_api_species_detail_404_for_unknown_id(client, seed_db):
    """GET /api/v1/species/<unknown_id> must return 404, not a 500 server error."""
    response = client.get('/api/v1/species/99999')
    assert response.status_code == 404
