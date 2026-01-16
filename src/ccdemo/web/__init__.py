"""Web UI blueprint."""

from flask import Blueprint

web_bp = Blueprint("web", __name__)

# Import routes to register them
from . import auth, sms

web_bp.register_blueprint(auth.web_auth_bp)
web_bp.register_blueprint(sms.web_sms_bp)
