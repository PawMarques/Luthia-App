"""Environment-based configuration for the Luthia Flask application.

Select a config class by setting the APP_ENV environment variable:
    APP_ENV=development  (default)
    APP_ENV=testing

Example .env entry:
    APP_ENV=development
"""

import os

basedir = os.path.abspath(os.path.dirname(__file__))


class BaseConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(
        os.path.dirname(basedir), 'luthia-data', 'product-images'
    )
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-only-insecure-key')


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(basedir, "luthia.db")}'


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


CONFIG_MAP = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
}
