"""Flask extensions initialization."""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def init_db(app):
    """Initialize database extension.

    Args:
        app: Flask application instance.
    """
    db.init_app(app)


def init_login(app):
    """Initialize login manager extension.

    Args:
        app: Flask application instance.
    """
    login_manager.init_app(app)


def init_csrf(app):
    """Initialize CSRF protection.

    Args:
        app: Flask application instance.
    """
    csrf.init_app(app)


def init_all(app):
    """Initialize all extensions.

    Args:
        app: Flask application instance.
    """
    init_db(app)
    init_login(app)
    init_csrf(app)


# Re-exports for backwards compatibility
# Tests import db and login_manager directly from smspanel.extensions
__all__ = ["db", "login_manager", "csrf", "init_db", "init_login", "init_csrf", "init_all"]

