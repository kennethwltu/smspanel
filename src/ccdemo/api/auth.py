"""API authentication endpoints."""

import jwt
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_user

from .. import db, login_manager
from ..models import User

api_auth_bp = Blueprint("api_auth", __name__)


@api_auth_bp.route("/auth/login", methods=["POST"])
def login() -> tuple:
    """Login and return JWT token.

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

    # Generate JWT token
    token_payload = {
        "user_id": user.id,
        "username": user.username,
        "exp": datetime.now(timezone.utc) + current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES", timedelta(hours=24)),
    }

    token = jwt.encode(token_payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")

    return jsonify({"access_token": token, "user_id": user.id, "username": user.username}), 200


@api_auth_bp.route("/auth/logout", methods=["POST"])
def logout() -> tuple:
    """Logout endpoint (JWT is stateless, so this is mainly for API compatibility).

    Returns:
        JSON response with success message.
    """
    return jsonify({"message": "Logged out successfully"}), 200
