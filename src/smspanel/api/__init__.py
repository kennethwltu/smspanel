"""API blueprint for RESTful endpoints."""

from flask import Blueprint

api_bp = Blueprint("api", __name__)

# Import routes to register them
from . import sms  # noqa: E402

api_bp.register_blueprint(sms.api_sms_bp)
