"""Flask application configuration classes.

Environment Variables:
    Required:
        DATABASE_URL - SQLAlchemy database connection string
        SECRET_KEY - Flask session encryption (min 32 chars, required in production)
        SMS_BASE_URL - SMS gateway URL
        SMS_APPLICATION_ID - SMS API app ID
        SMS_SENDER_NUMBER - SMS sender number

    Optional (with defaults):
        ADMIN_PASSWORD - Admin user password (auto-generated if not set)
"""

import os
import warnings
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""

    # Flask - SECRET_KEY must be set in production!
    SECRET_KEY = os.getenv("SECRET_KEY")

    # Flask-WTF CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.getenv("SECRET_KEY")  # Same as SECRET_KEY
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour in seconds

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///sms.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Connection Pool Settings (for MySQL in production)
    # These are ignored by SQLite but used by MySQL/PostgreSQL
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_POOL_MAX_OVERFLOW = 20
    SQLALCHEMY_POOL_RECYCLE = 3600  # Recycle connections after 1 hour
    SQLALCHEMY_POOL_PRE_PING = True  # Verify connections before use

    # SMS request timeout in seconds
    SMS_REQUEST_TIMEOUT = 30

    # SMS Gateway
    SMS_BASE_URL = os.getenv("SMS_BASE_URL")
    SMS_APPLICATION_ID = os.getenv("SMS_APPLICATION_ID")
    SMS_SENDER_NUMBER = os.getenv("SMS_SENDER_NUMBER")

    # SMS Queue
    SMS_QUEUE_WORKERS = 4
    SMS_QUEUE_MAX_SIZE = 1000

    # SMS Rate Limiting
    SMS_RATE_PER_SEC: float = 2.0
    SMS_BURST_CAPACITY: int = 4


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True

    def __init__(self):
        super().__init__()
        # Use a dev key only in development (warn in logs)
        if self.SECRET_KEY is None:
            warnings.warn(
                "SECRET_KEY not set, using development default. "
                "Set SECRET_KEY environment variable for production!"
            )
            self.SECRET_KEY = "dev-secret-key-change-in-production"
            # Also set CSRF secret key to the same value
            self.WTF_CSRF_SECRET_KEY = self.SECRET_KEY


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False

    def __init__(self):
        super().__init__()
        # SECRET_KEY is required in production
        if self.SECRET_KEY is None:
            raise ValueError(
                "SECRET_KEY environment variable is required in production. "
                "Set it before starting the application."
            )
        # Ensure key is sufficiently long
        if len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long.")


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False

    # Set a test SECRET_KEY for testing environment
    SECRET_KEY = "test-secret-key-for-testing-environment-only"
    # Also set CSRF secret key to the same value
    WTF_CSRF_SECRET_KEY = "test-secret-key-for-testing-environment-only"

    # SMS Gateway (for testing)
    SMS_BASE_URL = "https://test-sms-gateway.example.com/gateway/gateway.jsp"
    SMS_APPLICATION_ID = "test-app"
    SMS_SENDER_NUMBER = "test-sender"


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
