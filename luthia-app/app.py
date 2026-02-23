"""Luthia — tonewood price comparison tool for luthiers.

Entry point: creates the Flask application, registers all blueprints,
initialises extensions, and ensures database tables exist on first run.

Usage:
    python app.py          # development server on http://localhost:5000
"""

import os
from typing import Optional

from flask import Flask, redirect, url_for

from helpers import VENDOR_FLAGS
from models import db
from routes.browse    import browse_bp
from routes.builds    import builds_bp
from routes.images    import images_bp
from routes.templates import templates_bp
from routes.vendors    import vendors_bp
from routes.species    import species_bp
from routes.fret       import fret_bp


def create_app(test_config: Optional[dict] = None) -> Flask:
    """Application factory.

    Isolated from module-level execution so test suites can instantiate the
    app without triggering side-effects like database creation.

    Args:
        test_config: Optional dict of config values that override the defaults.
                     Pass TESTING=True and SQLALCHEMY_DATABASE_URI for test runs.
    """
    app = Flask(__name__)

    basedir = os.path.abspath(os.path.dirname(__file__))

    app.config['SQLALCHEMY_DATABASE_URI']  = f'sqlite:///{os.path.join(basedir, "luthia.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'product-images')

    # Apply test overrides before makedirs and db.init_app so they take effect.
    if test_config:
        app.config.update(test_config)

    # Ensure the image upload directory exists on first run.
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)

    # Jinja2 template filter: convert a country name to its flag emoji.
    @app.template_filter('vendor_flag')
    def vendor_flag_filter(country: str) -> str:
        return VENDOR_FLAGS.get(country or '', '')

    app.register_blueprint(browse_bp)
    app.register_blueprint(builds_bp)
    app.register_blueprint(images_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(vendors_bp)
    app.register_blueprint(species_bp)
    app.register_blueprint(fret_bp)

    @app.route('/')
    def index():
        return redirect(url_for('builds.builds_index'))

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == '__main__':
    print('\n' + '=' * 50)
    print('Luthia is starting...')
    print('Open your browser and go to: http://localhost:5000')
    print('Press CTRL+C to stop the server')
    print('=' * 50 + '\n')
    app.run(debug=True, port=5000)