"""Image management API endpoints.

Provides:
  POST   /api/v1/products/<id>/images  — upload a file or add a URL-based image
  DELETE /api/v1/images/<id>           — delete an image and its backing file
  PATCH  /api/v1/images/<id>/caption   — update the caption text of an image
"""

import os
import uuid

from flask import Blueprint, current_app, jsonify, request, send_from_directory

from helpers import allowed_file, api_error, fmt_image
from models import Product, ProductImage, db

images_bp = Blueprint('images', __name__)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@images_bp.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


@images_bp.route('/api/v1/products/<int:product_id>/images', methods=['POST'])
def api_image_upload(product_id):
    """Upload a file or save a URL as a product image."""
    # Verify the product exists before attaching images to it.
    Product.query.get_or_404(product_id)

    if request.is_json:
        return _save_url_image(product_id, request.get_json(force=True))
    return _save_file_image(product_id)


@images_bp.route('/api/v1/images/<int:image_id>', methods=['DELETE'])
def api_image_delete(image_id):
    """Delete a product image record and remove the backing file if it was uploaded."""
    img = ProductImage.query.get_or_404(image_id)

    if img.source_type == 'upload' and img.filename:
        path = os.path.join(current_app.config['UPLOAD_FOLDER'], img.filename)
        if os.path.exists(path):
            os.remove(path)

    db.session.delete(img)
    db.session.commit()
    return jsonify({'ok': True})


@images_bp.route('/api/v1/images/<int:image_id>/caption', methods=['PATCH'])
def api_image_caption(image_id):
    """Update the caption text of an existing image."""
    img = ProductImage.query.get_or_404(image_id)
    data = request.get_json(force=True)
    img.caption = (data.get('caption') or '').strip()
    db.session.commit()
    return jsonify({'ok': True, 'image': fmt_image(img)})


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _save_url_image(product_id: int, data: dict):
    """Persist an external URL image record and return the new image JSON."""
    url = (data.get('url') or '').strip()
    if not url:
        return api_error('No URL provided.')

    caption   = (data.get('caption') or '').strip()
    img = ProductImage(
        product_id=product_id,
        source_type='url',
        url=url,
        caption=caption,
        sort_order=_next_sort_order(product_id),
    )
    db.session.add(img)
    db.session.commit()
    return jsonify({'ok': True, 'image': fmt_image(img)})


def _save_file_image(product_id: int):
    """Validate and persist an uploaded file image record."""
    if 'file' not in request.files:
        return api_error('No file provided.')

    f = request.files['file']
    if not f.filename:
        return api_error('Empty filename.')
    if not allowed_file(f.filename):
        return api_error('File type not allowed. Use JPG, PNG, WebP or GIF.')

    ext      = f.filename.rsplit('.', 1)[1].lower()
    # Prefix the UUID filename with the product_id for easier manual identification.
    filename = f'{product_id}_{uuid.uuid4().hex}.{ext}'
    f.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

    caption = (request.form.get('caption') or '').strip()
    img = ProductImage(
        product_id=product_id,
        source_type='upload',
        filename=filename,
        caption=caption,
        sort_order=_next_sort_order(product_id),
    )
    db.session.add(img)
    db.session.commit()
    return jsonify({'ok': True, 'image': fmt_image(img)})


def _next_sort_order(product_id: int) -> int:
    """Return max(sort_order) + 1 for a product's images, or 1 if none exist yet."""
    current_max = (
        db.session.query(db.func.max(ProductImage.sort_order))
        .filter_by(product_id=product_id)
        .scalar()
    )
    return (current_max or 0) + 1
