"""Luthia — tonewood price comparison tool for luthiers.

Entry point: creates the Flask application, registers all blueprints,
initialises extensions, and ensures database tables exist on first run.

Usage:
    python app.py          # development server on http://localhost:5000
"""

import os
from typing import Optional

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, url_for
from flask_cors import CORS

load_dotenv()

from config import CONFIG_MAP, DevelopmentConfig
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

    config_class = CONFIG_MAP.get(os.environ.get('APP_ENV', ''), DevelopmentConfig)
    app.config.from_object(config_class)

    # Apply test overrides after class config so they take full effect.
    if test_config:
        app.config.update(test_config)

    # Ensure the image upload directory exists on first run.
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)

    # Configure CORS for development only (production will be same-domain)
    if app.config.get('ENV') == 'development' or app.debug:
        CORS(app, origins=['http://localhost:5173', 'http://localhost:5174'])

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

    @app.errorhandler(404)
    def not_found(e):
        return render_template(
            'errors/404.html',
            active_nav='',
            page_title='Luthia · Not Found',
            breadcrumb=[('Not Found', None)],
        ), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template(
            'errors/500.html',
            active_nav='',
            page_title='Luthia · Error',
            breadcrumb=[('Error', None)],
        ), 500

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