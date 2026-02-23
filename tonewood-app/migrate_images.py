"""
Migration: add product_images table
Run once: python3 migrate_images.py
Safe to run multiple times — skips if table already exists.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from models import db

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "luthia.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    # Check if table already exists
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    if 'product_images' in inspector.get_table_names():
        print('product_images table already exists — nothing to do.')
    else:
        db.engine.execute = db.engine.connect  # compat shim
        with db.engine.connect() as conn:
            conn.execute(text('''
                CREATE TABLE product_images (
                    image_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id  INTEGER NOT NULL REFERENCES products(product_id),
                    source_type VARCHAR(10) NOT NULL DEFAULT "upload",
                    filename    VARCHAR(200),
                    url         VARCHAR(500),
                    caption     VARCHAR(200),
                    sort_order  INTEGER DEFAULT 0,
                    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            '''))
            conn.commit()
        print('Created product_images table.')

    # Create upload folder
    upload_folder = os.path.join(basedir, 'static', 'product-images')
    os.makedirs(upload_folder, exist_ok=True)
    print(f'Upload folder ready: {upload_folder}')
    print('Migration complete.')