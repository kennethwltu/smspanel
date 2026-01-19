"""Configuration for the SMS application.

Environment Variables:
    Required:
        DATABASE_URL - SQLAlchemy database connection string
        HKT_BASE_URL - HKT SMS gateway URL
        HKT_APPLICATION_ID - HKT SMS API application ID
        HKT_SENDER_NUMBER - HKT SMS sender number

    Optional (with defaults):
        SECRET_KEY - Flask session encryption (default: dev key)
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""

    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///sms.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # HKT SMS
    HKT_BASE_URL = os.getenv("HKT_BASE_URL")
    HKT_APPLICATION_ID = os.getenv("HKT_APPLICATION_ID")
    HKT_SENDER_NUMBER = os.getenv("HKT_SENDER_NUMBER")


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
