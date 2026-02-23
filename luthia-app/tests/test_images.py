"""Integration tests for the images blueprint.

Tests the full image lifecycle: adding a URL image, uploading a file image,
editing a caption, and deleting an image.

File uploads use ``io.BytesIO`` for the fake file payload so no real image
file needs to exist on disk.  Actual file I/O (``f.save()``) is mocked out so
tests never touch the real filesystem beyond the temporary UPLOAD_FOLDER that
the test application config points to.
"""

import io
import json
from unittest.mock import patch

from models import ProductImage, db


# ---------------------------------------------------------------------------
# URL image
# ---------------------------------------------------------------------------

def test_post_url_image_saves_record(client, seed_db):
    """POST /api/products/<id>/images with JSON {url, caption} must persist a URL image.

    The image panel lets users link external product photos without uploading a
    file; this route is the only path that creates those records.
    """
    product_id = seed_db['products'][0].product_id
    payload    = {
        'url':     'https://example.com/ash-body-blank.jpg',
        'caption': 'Top view of the blank',
    }

    response = client.post(
        f'/api/products/{product_id}/images',
        data=json.dumps(payload),
        content_type='application/json',
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body['ok'] is True

    img = body['image']
    assert img['source_type'] == 'url'
    assert img['src']         == payload['url']
    assert img['caption']     == payload['caption']

    # Verify the record was written to the database
    record = db.session.get(ProductImage, img['image_id'])
    assert record is not None
    assert record.source_type == 'url'
    assert record.url         == payload['url']


def test_post_url_image_missing_url_returns_400(client, seed_db):
    """POST with an empty url field must return 400 and not create a record.

    An image with no URL or file is useless; the API must reject it rather than
    write a null row that would render as a broken image.
    """
    product_id = seed_db['products'][0].product_id

    response = client.post(
        f'/api/products/{product_id}/images',
        data=json.dumps({'url': '', 'caption': 'no url'}),
        content_type='application/json',
    )

    assert response.status_code == 400
    assert response.get_json()['ok'] is False


def test_post_url_image_for_unknown_product_returns_404(client, db_session):
    """POST to a non-existent product_id must return 404, not a 500."""
    response = client.post(
        '/api/products/99999/images',
        data=json.dumps({'url': 'https://example.com/x.jpg'}),
        content_type='application/json',
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# File upload image
# ---------------------------------------------------------------------------

def test_post_file_upload_saves_record(client, seed_db):
    """POST /api/products/<id>/images with a multipart file must persist an upload image.

    The fake file uses io.BytesIO so no real image file is needed; f.save() is
    patched to prevent any write to the temporary UPLOAD_FOLDER.
    """
    product_id = seed_db['products'][0].product_id
    fake_bytes = io.BytesIO(b'\x89PNG\r\n\x1a\n' + b'\x00' * 32)  # minimal fake PNG header

    with patch('routes.images.os.path.join', return_value='/dev/null'), \
         patch('werkzeug.datastructures.file_storage.FileStorage.save'):
        response = client.post(
            f'/api/products/{product_id}/images',
            data={
                'file':    (fake_bytes, 'blank.png'),
                'caption': 'Upload test',
            },
            content_type='multipart/form-data',
        )

    assert response.status_code == 200
    body = response.get_json()
    assert body['ok'] is True

    img = body['image']
    assert img['source_type'] == 'upload'
    assert img['caption']     == 'Upload test'
    # The src must follow the /static/product-images/<filename> pattern
    assert img['src'].startswith('/static/product-images/')


def test_post_file_upload_disallowed_extension_returns_400(client, seed_db):
    """Uploading a .txt file must return 400; allowed_file should reject it.

    This guards against attempts to upload arbitrary files through the image API.
    """
    product_id = seed_db['products'][0].product_id
    fake_bytes = io.BytesIO(b'not an image')

    response = client.post(
        f'/api/products/{product_id}/images',
        data={'file': (fake_bytes, 'exploit.txt')},
        content_type='multipart/form-data',
    )

    assert response.status_code == 400
    assert response.get_json()['ok'] is False


# ---------------------------------------------------------------------------
# Caption update (PATCH)
# ---------------------------------------------------------------------------

def test_patch_caption_updates_text(client, seed_db):
    """PATCH /api/images/<id>/caption must update the caption and return {ok: true}.

    Users can edit captions after upload; if this endpoint fails, caption edits
    are silently discarded and the original text is displayed forever.
    """
    # Seed a URL image directly so the test doesn't depend on the upload path
    product_id = seed_db['products'][0].product_id
    img = ProductImage(
        product_id=product_id,
        source_type='url',
        url='https://example.com/photo.jpg',
        caption='Original caption',
        sort_order=1,
    )
    db.session.add(img)
    db.session.commit()

    response = client.patch(
        f'/api/images/{img.image_id}/caption',
        data=json.dumps({'caption': 'Updated caption'}),
        content_type='application/json',
    )

    assert response.status_code == 200
    assert response.get_json()['ok'] is True

    # Reload and confirm the caption was persisted
    db.session.expire(img)
    assert img.caption == 'Updated caption'


def test_patch_caption_strips_whitespace(client, seed_db):
    """PATCH caption with surrounding whitespace should store the stripped value."""
    product_id = seed_db['products'][0].product_id
    img = ProductImage(
        product_id=product_id,
        source_type='url',
        url='https://example.com/x.jpg',
        caption='',
        sort_order=2,
    )
    db.session.add(img)
    db.session.commit()

    client.patch(
        f'/api/images/{img.image_id}/caption',
        data=json.dumps({'caption': '   Trimmed   '}),
        content_type='application/json',
    )

    db.session.expire(img)
    assert img.caption == 'Trimmed'


# ---------------------------------------------------------------------------
# Image deletion (DELETE)
# ---------------------------------------------------------------------------

def test_delete_image_removes_record(client, seed_db):
    """DELETE /api/images/<id> must remove the image record and return {ok: true}.

    After deletion the image must no longer be retrievable from the database,
    confirming the DELETE route calls db.session.delete() and commits.
    """
    product_id = seed_db['products'][0].product_id
    img = ProductImage(
        product_id=product_id,
        source_type='url',
        url='https://example.com/to-delete.jpg',
        caption='',
        sort_order=1,
    )
    db.session.add(img)
    db.session.commit()

    image_id = img.image_id

    response = client.delete(f'/api/images/{image_id}')

    assert response.status_code == 200
    assert response.get_json()['ok'] is True

    # Record must be gone
    assert db.session.get(ProductImage, image_id) is None


def test_delete_image_404_for_unknown_id(client, db_session):
    """DELETE /api/images/<unknown_id> must return 404, not a 500."""
    response = client.delete('/api/images/99999')
    assert response.status_code == 404
