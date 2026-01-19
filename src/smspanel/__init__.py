"""smspanel application factory."""

from datetime import datetime, timedelta, timezone
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

# Hong Kong Time is UTC+8
HKT_OFFSET = timedelta(hours=8)
HKT_TZ = timezone(HKT_OFFSET)


def format_hkt(dt: datetime) -> str:
    """Format a datetime to Hong Kong Time (HKT) string.

    Args:
        dt: datetime object (timezone-aware or naive)

    Returns:
        Formatted string in HKT (YYYY-MM-DD HH:MM:SS.mmm HKT)
    """
    if dt is None:
        return ""
    # If datetime is naive, assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # Convert to HKT
    hkt_dt = dt.astimezone(HKT_TZ)
    # Include milliseconds for precise timing
    return hkt_dt.strftime("%Y-%m-%d %H:%M:%S.") + f"{hkt_dt.microsecond // 1000:03d} HKT"


def create_app(config_name: str = "default") -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder="templates", static_folder="../static")

    # Load configuration
    from .config import config as config_dict

    app.config.from_object(config_dict.get(config_name, config_dict["default"]))

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "web.web_auth.login"
    login_manager.login_message = "Please log in to access this page."

    # Register blueprints
    from .api import api_bp
    from .web import web_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(web_bp)

    # Register custom template filters
    app.jinja_env.filters["hkt"] = format_hkt

    # Initialize task queue
    from .services.queue import init_task_queue

    num_workers = app.config.get("SMS_QUEUE_WORKERS", 4)
    max_queue_size = app.config.get("SMS_QUEUE_MAX_SIZE", 1000)
    init_task_queue(app, num_workers=num_workers, max_queue_size=max_queue_size)

    # Initialize admin account if it doesn't exist
    with app.app_context():
        db.create_all()  # Create all tables first
        from .models import User

        admin_user = User.query.filter_by(username="SMSadmin").first()
        if admin_user is None:
            admin = User(username="SMSadmin")
            admin.set_password("SMSpass#12")
            admin.token = User.generate_token()
            admin.is_admin = True
            admin.is_active = True

            db.session.add(admin)
            db.session.commit()

    return app
