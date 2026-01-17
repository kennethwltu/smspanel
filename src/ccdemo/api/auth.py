"""API authentication endpoints."""

from flask import Blueprint, request, jsonify

from .. import db
from ..models import User

api_auth_bp = Blueprint("api_auth", __name__)


@api_auth_bp.route("/auth/login", methods=["POST"])
def login() -> tuple:
    """Login and return API token.

    Request body (JSON):
        username: str
        password: str

    Returns:
        JSON response with access_token or error message.
    """
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user = User.query.filter_by(username=username).first()

    if user is None or not user.check_password(password):
        return jsonify({"error": "Invalid username or password"}), 401

    if not user.token:
        user.token = User.generate_token()
        db.session.commit()

    return jsonify({"access_token": user.token, "user_id": user.id, "username": user.username}), 200


@api_auth_bp.route("/auth/logout", methods=["POST"])
def logout() -> tuple:
    """Logout endpoint (token-based auth is stateless, so this is mainly for API compatibility).

    Returns:
        JSON response with success message.
    """
    return jsonify({"message": "Logged out successfully"}), 200
