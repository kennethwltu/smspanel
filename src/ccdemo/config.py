"""Configuration for the SMS application."""

import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""

    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///sms.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.getenv("SECRET_KEY", "jwt-secret-key"))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # HKT SMS
    HKT_BASE_URL = "https://cst01.1010.com.hk/gateway/gateway.jsp"
    HKT_APPLICATION_ID = os.getenv("HKT_APPLICATION_ID", "LabourDept")
    HKT_SENDER_NUMBER = os.getenv("HKT_SENDER_NUMBER", "852520702793127")

    # API Key for REST auth (fallback)
    API_KEY = os.getenv("API_KEY", "default-api-key-for-development")


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
