"""Application factory for creating and configuring Flask app."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from flask import Flask, g, request

from smspanel.config import ConfigService
from smspanel.extensions import db, init_all
from smspanel.models import User


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

    # Setup logging
    _setup_logging(app)

    # Initialize extensions
    init_all(app)

    # Configure login manager
    from smspanel.extensions import login_manager

    login_manager.login_view = "web.web_auth.login"
    login_manager.login_message = "Please log in to access this page."

    # Register template filters
    _register_filters(app)

    # Register before/after request handlers for request ID tracking
    @app.before_request
    def before_request():
        from smspanel.utils.logging import set_request_id, generate_request_id

        req_id = request.headers.get("X-Request-ID") or generate_request_id()
        set_request_id(req_id)
        g.start_time = datetime.now(timezone.utc)

    @app.after_request
    def after_request(response):
        from smspanel.utils.logging import log_request

        if hasattr(g, "start_time"):
            duration_ms = (datetime.now(timezone.utc) - g.start_time).total_seconds() * 1000
        else:
            duration_ms = 0

        log_request(request, response.status_code, duration_ms)
        return response

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
    import os
    import tempfile
    import stat
    from smspanel.config import config as config_dict

    app.config.from_object(config_dict.get(config_name, config_dict["default"]))

    # For Docker environments, use the volume-mounted path /app/instance/sms.db
    # Check if we're running in Docker by checking for /app directory
    if os.path.exists('/app'):
        # Use the volume-mounted path for persistence
        volume_db_path = '/app/instance/sms.db'
        print(f"Running in Docker container, using volume-mounted database: {volume_db_path}")
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{volume_db_path}'
        
        # Ensure the instance directory exists and is writable
        instance_dir = '/app/instance'
        try:
            if not os.path.exists(instance_dir):
                os.makedirs(instance_dir, exist_ok=True)
                print(f"Created instance directory: {instance_dir}")
            
            # Test if directory is writable
            test_file = os.path.join(instance_dir, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.unlink(test_file)
            print(f"Instance directory {instance_dir} is writable")
        except Exception as e:
            print(f"Warning: Instance directory {instance_dir} is not writable: {e}")
            # Fallback to /tmp/sms.db if volume is not writable
            tmp_db_path = '/tmp/sms.db'
            app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{tmp_db_path}'
            print(f"Falling back to temporary database: {tmp_db_path}")
    else:
        # For non-Docker environments, check if SQLite database directory is writable
        db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if db_url.startswith('sqlite:///'):
            db_path = db_url[10:]  # Remove 'sqlite:///'
            db_dir = os.path.dirname(db_path) if os.path.dirname(db_path) else '.'
            
            # Check if directory is writable
            # Try to create a test file to check writability
            test_file = os.path.join(db_dir, '.write_test')
            try:
                # Try to create directory if it doesn't exist
                if db_dir and not os.path.exists(db_dir):
                    os.makedirs(db_dir, exist_ok=True)
                
                # Try to write a test file
                with open(test_file, 'w') as f:
                    f.write('test')
                os.unlink(test_file)
                print(f"Database directory {db_dir} is writable, using {db_path}")
            except Exception as e:
                # Directory is not writable, use /tmp instead
                print(f"Database directory {db_dir} is not writable: {e}")
                tmp_db_path = os.path.join(tempfile.gettempdir(), 'sms.db')
                app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{tmp_db_path}'
                print(f"Using temporary database: {tmp_db_path}")

    # Initialize config service for SMS
    config_service = ConfigService(
        base_url=app.config.get("SMS_BASE_URL"),
        application_id=app.config.get("SMS_APPLICATION_ID"),
        sender_number=app.config.get("SMS_SENDER_NUMBER"),
    )

    # Initialize SMS helper with config service
    from smspanel.utils.sms_helper import init_sms_service

    init_sms_service(config_service)

    # Initialize rate limiter
    from smspanel.utils.rate_limiter import init_rate_limiter

    rate_per_sec = app.config.get("SMS_RATE_PER_SEC", 2.0)
    burst_capacity = app.config.get("SMS_BURST_CAPACITY", 4)
    init_rate_limiter(rate_per_sec=rate_per_sec, burst_capacity=burst_capacity)


def _setup_logging(app: Flask) -> None:
    """Configure application logging.

    Args:
        app: Flask application instance.
    """
    from smspanel.utils.logging import setup_app_logging

    setup_app_logging(app)


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
    from smspanel.api import api_bp
    from smspanel.web import web_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(web_bp)


def _init_task_queue(app: Flask) -> None:
    """Initialize task queue for SMS processing.

    Args:
        app: Flask application instance.
    """
    from smspanel.services.queue import init_task_queue

    num_workers = app.config.get("SMS_QUEUE_WORKERS", 4)
    max_queue_size = app.config.get("SMS_QUEUE_MAX_SIZE", 1000)
    init_task_queue(app, num_workers=num_workers, max_queue_size=max_queue_size)


def _ensure_admin_user(app: Flask) -> None:
    """Ensure default admin user exists.

    Admin credentials are read from environment variables:
    - ADMIN_PASSWORD: Admin password (auto-generated if not set)

    Args:
        app: Flask application instance.
    """
    import secrets
    import string
    from os import getenv

    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully.")
            
            # Create admin user if it doesn't exist
            admin_user = User.query.filter_by(username="SMSadmin").first()
            if admin_user is None:
                # Get admin password from env or generate one
                admin_password = getenv("ADMIN_PASSWORD")
                if admin_password is None:
                    # Generate a secure random password
                    alphabet = string.ascii_letters + string.digits
                    admin_password = "".join(secrets.choice(alphabet) for _ in range(16))
                    # In production, log warning about generated password
                    if not app.config.get("DEBUG", True):
                        app.logger.warning(
                            "Admin password was auto-generated. "
                            "Set ADMIN_PASSWORD environment variable to prevent this."
                        )

                admin = User(username="SMSadmin")
                admin.set_password(admin_password)
                admin.token = User.generate_token()
                admin.is_admin = True
                admin.is_active = True

                db.session.add(admin)
                db.session.commit()

                # Log the generated password in development only
                if getenv("ADMIN_PASSWORD") is None and app.config.get("DEBUG", False):
                    print(f"\n[DEV] Generated admin password: {admin_password}\n")
        except Exception as e:
            print(f"Failed to create database or admin user: {e}")
            print("App will start without admin user. Database operations may fail.")
            # Don't raise - allow app to start without admin user
