"""Application factory for creating and configuring Flask app."""

from datetime import timedelta, timezone
from typing import Optional

from flask import Flask

from .config import ConfigService
from .extensions import db, csrf, init_all
from .models import User


def create_app(config_name: Optional[str] = None) -> Flask:
    """Create and configure Flask application.

    Args:
        config_name: Configuration environment name (e.g., 'development', 'production').

    Returns:
        Configured Flask application.
    """
    app = Flask(__name__, template_folder="templates", static_folder="../static")

    # Load configuration
    _load_config(app, config_name)

    # Initialize extensions
    init_all(app)

    # Configure login manager
    from .extensions import login_manager
    login_manager.login_view = "web.web_auth.login"
    login_manager.login_message = "Please log in to access this page."

    # Register template filters
    _register_filters(app)

    # Register blueprints
    _register_blueprints(app)

    # Initialize task queue
    _init_task_queue(app)

    # Ensure admin user exists
    _ensure_admin_user(app)

    return app


def _load_config(app: Flask, config_name: Optional[str]) -> None:
    """Load application configuration.

    Args:
        app: Flask application instance.
        config_name: Configuration name.
    """
    from .config import config as config_dict

    app.config.from_object(config_dict.get(config_name, config_dict["default"]))

    # Initialize config service for SMS
    config_service = ConfigService(
        base_url=app.config.get("SMS_BASE_URL"),
        application_id=app.config.get("SMS_APPLICATION_ID"),
        sender_number=app.config.get("SMS_SENDER_NUMBER"),
    )

    # Initialize SMS helper with config service
    from .utils.sms_helper import init_sms_service
    init_sms_service(config_service)


def _register_filters(app: Flask) -> None:
    """Register custom Jinja2 template filters.

    Args:
        app: Flask application instance.
    """
    HKT_OFFSET = timedelta(hours=8)
    HKT_TZ = timezone(HKT_OFFSET)

    def format_hkt(dt):
        """Format a datetime to Hong Kong Time (HKT) string."""
        if dt is None:
            return ""
        # If datetime is naive, assume UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # Convert to HKT
        hkt_dt = dt.astimezone(HKT_TZ)
        # Include milliseconds for precise timing
        return hkt_dt.strftime("%Y-%m-%d %H:%M:%S.") + f"{hkt_dt.microsecond // 1000:03d} HKT"

    app.jinja_env.filters["hkt"] = format_hkt


def _register_blueprints(app: Flask) -> None:
    """Register Flask blueprints.

    Args:
        app: Flask application instance.
    """
    from .api import api_bp
    from .web import web_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(web_bp)


def _init_task_queue(app: Flask) -> None:
    """Initialize task queue for SMS processing.

    Args:
        app: Flask application instance.
    """
    from .services.queue import init_task_queue

    num_workers = app.config.get("SMS_QUEUE_WORKERS", 4)
    max_queue_size = app.config.get("SMS_QUEUE_MAX_SIZE", 1000)
    init_task_queue(app, num_workers=num_workers, max_queue_size=max_queue_size)


def _ensure_admin_user(app: Flask) -> None:
    """Ensure default admin user exists.

    Args:
        app: Flask application instance.
    """
    with app.app_context():
        db.create_all()
        admin_user = User.query.filter_by(username="SMSadmin").first()
        if admin_user is None:
            admin = User(username="SMSadmin")
            admin.set_password("SMSpass#12")
            admin.token = User.generate_token()
            admin.is_admin = True
            admin.is_active = True

            db.session.add(admin)
            db.session.commit()
