"""Luthia — tonewood price comparison tool for luthiers.

Entry point: creates the Flask application, registers all blueprints,
initialises extensions, and ensures database tables exist on first run.

Usage:
    python app.py          # development server on http://localhost:5000
"""

import os

from flask import Flask, redirect, url_for

from models import db
from routes.browse    import browse_bp
from routes.builds    import builds_bp
from routes.images    import images_bp
from routes.templates import templates_bp


def create_app() -> Flask:
    """Application factory.

    Isolated from module-level execution so test suites can instantiate the
    app without triggering side-effects like database creation.
    """
    app = Flask(__name__)

    basedir = os.path.abspath(os.path.dirname(__file__))

    app.config['SQLALCHEMY_DATABASE_URI']  = f'sqlite:///{os.path.join(basedir, "luthia.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'product-images')

    # Ensure the image upload directory exists on first run.
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)

    app.register_blueprint(browse_bp)
    app.register_blueprint(builds_bp)
    app.register_blueprint(images_bp)
    app.register_blueprint(templates_bp)

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
